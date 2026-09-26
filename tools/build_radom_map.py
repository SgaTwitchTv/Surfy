"""Create the offline Radom road background and draft control-line inventory.

Input is a local OSM API 0.6 map XML extract. No source run is modified.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from greenwave.route_geometry import load_route


ROAD_KINDS = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
              'residential', 'unclassified', 'living_street', 'service',
              'primary_link', 'secondary_link', 'tertiary_link'}
SOURCE_URL = 'https://api.openstreetmap.org/api/0.6/map?bbox=21.126,51.388,21.162,51.395'
CONTROL_POINTS = {
    'radom_limanowskiego_25_czerwca_draft': (
        ('5316831070', 'LUKASIKA', '1905 Roku / Łukasika'),
        ('5316839131', 'OBRONCOW', '1905 Roku / Obrońców'),
        ('5316923129', 'MLODZIANOWSKA', '1905 Roku / Młodzianowska'),
        ('1875023568', 'DOWKONTTA', '1905 Roku / Dowkontta–Kościuszki'),
        ('1875023564', 'GRZECZNAROWSKIEGO', 'Grzecznarowskiego / Dowkontta'),
        ('4062286643', 'DWORCOWY', 'Poniatowskiego / plac Dworcowy'),
        ('4062286638', 'PRAZMOWSKIEGO', 'Beliny-Prażmowskiego przed rondem'),
    ),
    'radom_25_czerwca_limanowskiego_draft': (
        ('5382981369', 'PRAZMOWSKIEGO', 'Beliny-Prażmowskiego za rondem'),
        ('4062286641', 'DWORCOWY', 'Poniatowskiego / plac Dworcowy'),
        ('1846616301', 'GRZECZNAROWSKIEGO', 'Grzecznarowskiego / Dowkontta'),
        ('1846603614', 'DOWKONTTA', '1905 Roku / Dowkontta–Kościuszki'),
        ('5316932953', 'MLODZIANOWSKA', '1905 Roku / Młodzianowska'),
        ('1846568809', 'OBRONCOW', '1905 Roku / Obrońców'),
        ('1846578297', 'LUKASIKA', '1905 Roku / Łukasika'),
    ),
}


def read_osm(path):
    root = ET.parse(path).getroot()
    nodes = {}
    for element in root.findall('node'):
        nodes[element.attrib['id']] = (
            float(element.attrib['lon']), float(element.attrib['lat']),
            {tag.attrib['k']: tag.attrib['v'] for tag in element.findall('tag')})
    ways = []
    for element in root.findall('way'):
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in element.findall('tag')}
        if tags.get('highway') not in ROAD_KINDS:
            continue
        coords = [nodes[nd.attrib['ref']][:2] for nd in element.findall('nd')
                  if nd.attrib['ref'] in nodes]
        if len(coords) >= 2:
            ways.append(dict(type='Feature', properties=dict(
                name=tags.get('name', ''), kind=tags['highway'], osm_way_id=element.attrib['id']),
                geometry=dict(type='LineString', coordinates=coords)))
    return nodes, ways


def build(source):
    nodes, features = read_osm(source)
    map_data = dict(type='FeatureCollection', features=features, demo_route=[], metadata=dict(
        attribution='© OpenStreetMap contributors', license='ODbL 1.0',
        copyright_url='https://www.openstreetmap.org/copyright', source_url=SOURCE_URL,
        extracted_on='2026-09-23', bbox=[21.126, 51.388, 21.162, 51.395],
        marker_quality='DRAFT', notes='Offline street background for the Radom GPS pilot.'))
    map_path = ROOT / 'data/maps/radom.json'
    map_path.write_text(json.dumps(map_data, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    for route_id, candidates in CONTROL_POINTS.items():
        path = ROOT / 'data/routes' / f'{route_id}.json'
        route = load_route(path)
        raw = json.loads(path.read_text(encoding='utf-8'))
        stops = []
        for node_id, label_id, label in candidates:
            lon, lat, tags = nodes[node_id]
            if tags.get('highway') != 'traffic_signals':
                raise ValueError(f'OSM node {node_id} is not a signal')
            projection = route.project(lon, lat)[0]
            if projection.cross_track_m > 12:
                raise ValueError(f'{node_id} is {projection.cross_track_m:.1f} m from {route_id}')
            segment = projection.segment_index
            first, second = route.xy[segment:segment + 2]
            dx, dy = second[0] - first[0], second[1] - first[1]
            length = math.hypot(dx, dy)
            center = route.to_xy(projection.longitude, projection.latitude)
            normal = (-dy / length, dx / length)
            half_width = 8.0
            line = [route.to_wgs84(center[0] + sign * half_width * normal[0],
                                   center[1] + sign * half_width * normal[1])
                    for sign in (-1, 1)]
            stops.append(dict(
                stop_line_id=f'RD_{label_id}_{"OUT" if "limanowskiego_25" in route_id else "BACK"}',
                signal_id=None, segment_index=segment, coordinates=line,
                direction='FORWARD', movement='UNCONFIRMED',
                source=dict(kind='OPENSTREETMAP_TRAFFIC_SIGNAL_NODE',
                            url=f'https://www.openstreetmap.org/node/{node_id}',
                            obtained_on='2026-09-23', label=label,
                            notes='Prostopadła linia przez projekcję węzła OSM na roboczą trasę; to nie jest pomiar linii zatrzymania.'),
                verification=dict(status='DRAFT', date='2026-09-23',
                                  notes='Właściwy sygnalizator, manewr i linia wymagają potwierdzenia terenowego.'),
                position_uncertainty_m=20))
        raw['geometry_version'] = 'gps-osm-draft-2026-09-23-v2'
        raw['stop_lines'] = stops
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        load_route(path)
        print(f'{route_id}: {len(stops)} draft control lines')
    print(f'{map_path}: {len(features)} roads')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('osm_xml', type=Path)
    build(parser.parse_args().osm_xml)
