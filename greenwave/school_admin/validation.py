"""Strict DTO schemas followed by existing GreenWave domain validators."""
import copy
import json
import math
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from greenwave.models import Corridor, SignalModel, SignalType
from greenwave.prediction import PredictionSettings, SignalRelation
from greenwave.route_geometry import load_route
from greenwave.school_accounts.errors import AuthError


def keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys()-set(required)-set(optional):
        raise ValueError('Missing or unknown fields')


def source(value):
    keys(value, {'attribution'}, {'description','url'})
    if 'url' in value:
        parsed=urlsplit(value['url'])
        if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Invalid source URL')
    if 'description' in value and (not isinstance(value['description'],str) or len(value['description'])>1000):raise ValueError('Source description')
    if not isinstance(value['attribution'], str) or not 1 <= len(value['attribution']) <= 500: raise ValueError('Attribution required')


def safe_tree(value, depth=0, source_metadata=False):
    if depth > 20: raise ValueError('Too deeply nested')
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {'verified','verification','geometry_verification','data_quality','last_verified','field_checked','path','root','filename','raw_ref','token','password','owner_id'}:
                raise ValueError('Forbidden verification/storage field')
            if key=='url':
                if not source_metadata:raise ValueError('URL outside source metadata')
                parsed=urlsplit(child)
                if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Invalid metadata URL')
                continue  # Metadata only; never fetched or resolved.
            safe_tree(child, depth+1, key=='source')
    elif isinstance(value, list):
        if len(value)>10000: raise ValueError('Too many elements')
        for child in value: safe_tree(child,depth+1)
    elif isinstance(value,float) and not math.isfinite(value): raise ValueError('Nonfinite value')
    elif isinstance(value,str) and (len(value)>2000 or '://' in value or value.startswith(('/', '\\')) or '..' in value or (len(value)>1 and value[1]==':')):
        raise ValueError('Invalid text/path')


def payload(kind, supplied, *, stored=False):
    value=copy.deepcopy(supplied)
    try:
        # Stored server-assigned verification is removed only after checking exact values.
        if stored:
            def strip(v):
                if isinstance(v,dict):
                    for k in list(v):
                        if k in {'verification','geometry_verification'}:
                            if v.pop(k)!={'status':'DRAFT'}: raise ValueError('Invalid verification')
                        elif k in {'verified','data_quality','last_verified'}:
                            expected={'verified':False,'data_quality':'UNVERIFIED','last_verified':None}[k]
                            if v.pop(k)!=expected: raise ValueError('Invalid verification')
                        else: strip(v[k])
                elif isinstance(v,list):
                    for child in v:strip(child)
            strip(value)
        safe_tree(value)
        if kind=='ROUTE':
            keys(value,{'schema_version','route_id','geometry_version','name','direction_description','source','coordinates'}, {'speed_sections','stop_lines'})
            source(value['source'])
            if type(value['schema_version']) is not int or value['schema_version']!=1: raise ValueError('Schema version')
            if not isinstance(value['coordinates'],list) or not 2<=len(value['coordinates'])<=10000:raise ValueError('Coordinates')
            value['geometry_verification']={'status':'DRAFT'}
            for section in value.get('speed_sections',[]):
                keys(section,{'start_s_m','end_s_m','limit_mps','source'});source(section['source']);section['verification']={'status':'DRAFT'}
            for line in value.get('stop_lines',[]):
                keys(line,{'stop_line_id','segment_index','coordinates','position_uncertainty_m','source'}, {'signal_id','direction','movement'})
                source(line['source']);line['verification']={'status':'DRAFT'}
            with TemporaryDirectory(prefix='gw-config-validation-') as tmp:
                path=Path(tmp)/'route.json';path.write_text(json.dumps(value,allow_nan=False),encoding='utf-8');load_route(path)
        elif kind=='SIGNAL':
            keys(value,{'schema_version','id','name','direction','speed_limit_mps','signals'})
            if type(value['schema_version']) is not int or value['schema_version']!=1: raise ValueError('Schema version')
            if not isinstance(value['signals'],list) or not 1<=len(value['signals'])<=1000: raise ValueError('Signals')
            for name in ('id','name','direction'):
                if not isinstance(value[name],str) or not 1<=len(value[name])<=120:raise ValueError('Corridor identity')
            models=[]
            names={f.name for f in fields(SignalModel)}-{'verified','data_quality','last_verified'}
            for signal in value['signals']:
                keys(signal,names)
                for name in ('id','name','direction','movement','source','notes'):
                    if not isinstance(signal[name],str) or len(signal[name])>1000 or (name!='notes' and not signal[name]):raise ValueError('Signal text')
                signal.update(verified=False,data_quality='UNVERIFIED',last_verified=None)
                models.append(SignalModel(**(signal|{'signal_type':SignalType(signal['signal_type'])})))
            if type(value['speed_limit_mps']) is bool:raise ValueError('Speed limit')
            Corridor(**{k:v for k,v in value.items() if k not in {'schema_version','signals'}},signals=tuple(models))
        elif kind=='MODEL':
            keys(value,{'schema_version','settings','relations'})
            if type(value['schema_version']) is not int or value['schema_version']!=1:raise ValueError('Schema version')
            keys(value['settings'],set(),{f.name for f in fields(PredictionSettings)})
            PredictionSettings(**value['settings'])
            if not isinstance(value['relations'],list) or len(value['relations'])>1000:raise ValueError('Relations')
            names={f.name for f in fields(SignalRelation)}-{'verified','data_quality'}
            seen=set()
            for relation in value['relations']:
                keys(relation,names)
                for name in ('source_signal_id','target_signal_id','source'):
                    if not isinstance(relation[name],str) or not 1<=len(relation[name])<=120:raise ValueError('Relation identity')
                for name in ('green_start_delta_seconds','uncertainty_seconds'):
                    if type(relation[name]) not in {int,float}:raise ValueError('Relation number')
                pair=(relation['source_signal_id'],relation['target_signal_id'])
                if pair in seen:raise ValueError('Duplicate relation')
                seen.add(pair);relation.update(verified=False,data_quality='UNVERIFIED');SignalRelation(**relation)
        else:raise ValueError('Kind')
        return value
    except (ValueError,TypeError,KeyError,OverflowError,AttributeError):
        raise AuthError(422,'VALIDATION',{'payload':'Nieprawidłowa konfiguracja: sprawdź pola, geometrię, fazy i relacje. Flagi weryfikacji i ścieżki są zabronione.'}) from None
