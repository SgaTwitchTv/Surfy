import json
from greenwave.school_accounts.errors import AuthError
from greenwave.school_resources.reads import scope,trip_dto,pick,OBS_FIELDS
from greenwave.school_resources.policy import resource_id
from .paging import Paging,dates


class Lists:
    def __init__(self,policy,key):self.policy,self.repo,self.paging=policy,policy.repo,Paging(policy.repo,key)
    def read(self,raw,q,kind):
        _,actor=self.policy.session(raw);shared=scope(q)=='shared'
        if shared:self.policy.role(raw,{'ANALYST'})
        if 'trip_id' in q:
            _,_,_,own=self.policy.trip(raw,q['trip_id'])
            if shared==own:raise AuthError(404,'NOT_FOUND')
        limit,sort,cur=self.paging.page(actor,kind,q)
        after,before=dates(q);obs=kind=='observations';alias='o' if obs else 't'
        column='server_received_at' if obs else 'created_at'
        clauses=["s.analyst_id=?","s.revoked_at IS NULL","t.status='COMPLETE'","t.archived_at IS NULL"] if shared else ['t.owner_id=?']
        values=[actor.user_id]
        archived=q.get('archived','false')
        if not obs:
            if shared and archived=='true':clauses.append('0')
            if archived not in {'true','false'}:raise AuthError(422,'VALIDATION')
            if not shared:clauses.append('t.archived_at IS '+('NOT ' if archived=='true' else '')+'NULL')
        if 'route_id' in q:
            from greenwave.school_data.validation import text
            text(q['route_id'],1,120)
            clauses.append("EXISTS(SELECT 1 FROM config_versions v WHERE v.id=t.route_version_id AND v.kind='ROUTE' AND v.logical_id=?)");values.append(q['route_id'])
        for name in ['trip_id']:
            if name in q:resource_id(q[name]);clauses.append('t.'+('route_version_id' if name=='route_id' else 'id')+'=?');values.append(q[name])
        if not obs and 'status' in q:
            if q['status'] not in {'PLANNED','STARTING','RECORDING','FINALIZING','COMPLETE','INTERRUPTED'}:raise AuthError(422,'VALIDATION')
            clauses.append('t.status=?');values.append(q['status'])
        if obs:
            enums={'state':{'RED','YELLOW','GREEN','RED_YELLOW','OFF','UNKNOWN'},'event_type':{'STATE_SEEN','STATE_START'},'source':{'MANUAL','CV'},'valid':{'true','false'}}
            for name,allowed in enums.items():
                if name in q and q[name] not in allowed:raise AuthError(422,'VALIDATION')
            if 'signal_id' in q:
                from greenwave.school_data.validation import text
                text(q['signal_id'],1,120)
            for name in ['signal_id','source']:
                if name in q:clauses.append('o.'+name+'=?');values.append(q[name])
            for name in ['state','event_type','valid']:
                if name in q:
                    original='1' if name=='valid' else 'o.'+name
                    clauses.append("COALESCE(json_extract(k.after_json,'$."+name+"'),"+original+")=?")
                    values.append(int(q[name]=='true') if name=='valid' else q[name])
        clauses.append(alias+'.'+column+'<=?');values.append(cur['as_of'])
        for operator,value in [('>=',after),('<',before)]:
            if value is not None:clauses.append(alias+'.'+column+operator+'?');values.append(value)
        if cur['last']:
            operator='<' if sort=='desc' else '>'
            clauses.append('('+alias+'.'+column+','+alias+'.id) '+operator+' (?,?)');values.extend(cur['last'])
        join=' JOIN trip_shares s ON s.trip_id=t.id' if shared else ''
        base='observations o JOIN trips t ON t.id=o.trip_id LEFT JOIN observation_corrections k ON k.observation_id=o.id AND k.sequence=(SELECT max(sequence) FROM observation_corrections WHERE observation_id=o.id)' if obs else 'trips t'
        with self.repo.database.transaction(False) as c:
            self.repo.user(c,actor,{'ANALYST'} if shared else None)
            rows=[dict(r) for r in c.execute('SELECT '+alias+'.* FROM '+base+join+' WHERE '+' AND '.join(clauses)+' ORDER BY '+alias+'.'+column+' '+sort+','+alias+'.id '+sort+' LIMIT ?',(*values,limit+1))]
            rows,page=self.paging.result(rows,limit,cur,column)
            if obs:
                for row in rows:row['effective'],row['correction_revision']=self.repo.effective(c,row)
        items=[{**pick(r,OBS_FIELDS),'historical':bool(r['historical']),'journaling_state':r['journaling_state'],
                'original':pick(r,('state','event_type','server_received_at','measured_at'))} for r in rows] if obs else [trip_dto(r,not shared) for r in rows]
        return {'items':items,'page':page}
