"""Convert an official OSM API XML bbox extract into GreenWave's offline vector JSON."""
import argparse
from datetime import date
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROAD_KINDS = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
              'residential', 'living_street', 'service', 'motorway_link', 'trunk_link',
              'primary_link', 'secondary_link', 'tertiary_link'}


def convert(input_path, output_path, source_url):
    root = ET.parse(input_path).getroot()
    nodes = {node.attrib['id']: [float(node.attrib['lon']), float(node.attrib['lat'])]
             for node in root.findall('node')}
    features = []
    for way in root.findall('way'):
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
        highway = tags.get('highway')
        area_kind = ('building' if 'building' in tags else
                     'park' if tags.get('leisure') in ('park', 'garden', 'playground') or
                     tags.get('landuse') in ('grass', 'forest', 'recreation_ground') else None)
        if highway not in ROAD_KINDS and area_kind is None:
            continue
        coordinates = [nodes[item.attrib['ref']] for item in way.findall('nd') if item.attrib['ref'] in nodes]
        polygon = area_kind is not None and len(coordinates) >= 4 and coordinates[0] == coordinates[-1]
        if len(coordinates) < (4 if polygon else 2):
            continue
        features.append(dict(type='Feature',
            properties=dict(name=tags.get('name', ''), kind=area_kind or highway,
                            osm_way_id=way.attrib['id']),
            geometry=dict(type='Polygon' if polygon else 'LineString',
                          coordinates=[coordinates] if polygon else coordinates)))
    bounds = root.find('bounds')
    bbox = None if bounds is None else [float(bounds.attrib[key]) for key in ('minlon', 'minlat', 'maxlon', 'maxlat')]
    result = dict(type='FeatureCollection', features=features, demo_route=[], metadata=dict(
        attribution='© OpenStreetMap contributors', license='ODbL 1.0',
        copyright_url='https://www.openstreetmap.org/copyright', source_url=source_url,
        extracted_on=date.today().isoformat(), bbox=bbox, marker_quality='NONE',
        notes='Offline street extract for raw GPS display; contains no verified route or stop line.'))
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--source-url', required=True)
    args = parser.parse_args()
    convert(args.input, args.output, args.source_url)


if __name__ == '__main__':
    main()
