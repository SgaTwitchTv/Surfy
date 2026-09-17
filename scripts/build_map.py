"""Build a small offline map from an OSM XML extract, without network access.

Usage: python scripts/build_map.py path/to/extract.osm
The demo route follows the southbound carriageway in the available extract.
Control-point placement along it is deliberately synthetic, not surveyed.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def build(source: Path):
    root = ET.parse(source).getroot()
    nodes = {n.attrib['id']: [float(n.attrib['lon']), float(n.attrib['lat'])] for n in root.findall('node')}
    features, segments = [], {}
    for way in root.findall('way'):
        tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
        highway, land, leisure = tags.get('highway'), tags.get('landuse'), tags.get('leisure')
        if highway in ('footway', 'path', 'steps', 'cycleway', 'corridor', 'platform'):
            continue
        if not (highway or land or leisure == 'park' or 'building' in tags):
            continue
        refs = [n.attrib['ref'] for n in way.findall('nd')]
        if any(ref not in nodes for ref in refs):
            continue
        coords = [nodes[ref] for ref in refs]
        if len(coords) < 2:
            continue
        polygon = not highway and coords[0] == coords[-1]
        features.append(dict(type='Feature', properties=dict(name=tags.get('name', ''),
            kind=highway or ('park' if leisure == 'park' or land in ('grass', 'forest', 'recreation_ground') else 'building')),
            geometry=dict(type='Polygon' if polygon else 'LineString', coordinates=[coords] if polygon else coords)))
        if tags.get('name') == 'Żwirki i Wigury' and highway in ('primary', 'secondary', 'tertiary') and tags.get('oneway') == 'yes' and coords[0][1] > coords[-1][1]:
            segments[refs[0]] = (refs[-1], coords)
    if not segments:
        raise ValueError('Extract has no southbound route')
    current = max(segments, key=lambda node: nodes[node][1])
    route, visited = [], set()
    while current in segments and current not in visited:
        visited.add(current)
        end, coords = segments[current]
        route.extend(coords if not route else coords[1:])
        current = end
    return dict(type='FeatureCollection', features=features, demo_route=route,
        metadata=dict(attribution='© OpenStreetMap contributors', license='ODbL 1.0',
            copyright_url='https://www.openstreetmap.org/copyright',
            source_url='https://api.openstreetmap.org/api/0.6/map?bbox=20.985,52.201,20.994,52.215',
            extracted_on='2026-09-11', generated_on=date.today().isoformat(),
            marker_quality='PLACEHOLDER',
            notes='Offline street extract. Demo points are normalized along the available southbound route, not actual stop lines.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    data = build(args.source)
    output = Path(__file__).resolve().parents[1] / 'data/maps/warsaw.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'{len(data["features"])} features, {len(data["demo_route"])} route vertices -> {output}')
