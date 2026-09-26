"""Build the desk-checked Arkadia pilot fixture from saved OSM/OSRM sources."""
from __future__ import annotations

import argparse
from datetime import date
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


EARTH_RADIUS_M = 6_371_008.8
ROAD_KINDS = {
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'living_street', 'service', 'motorway_link', 'trunk_link',
    'primary_link', 'secondary_link', 'tertiary_link',
}

# One node on the intended carriageway for every desk-inventoried control point.
# These are OSM traffic-signal nodes, not surveyed stop-line coordinates.
CONTROL_POINTS = (
    ('12168894882', 'SL01_MACZKA_PEDESTRIAN', 'Maczka — przejście przed Rudnickiego'),
    ('34675218', 'SL02_MACZKA_RUDNICKIEGO', 'Maczka × Rudnickiego'),
    ('10028482222', 'SL03_RONDO_KATYNSKIE_ENTRY', 'Wjazd na rondo Ofiar Zbrodni Katyńskiej'),
    ('10028482225', 'SL04_RONDO_KATYNSKIE_EXIT', 'Wyjazd z ronda w Powązkowską'),
    ('9797089261', 'SL05_POWAZKOWSKA_CEMETERY', 'Powązkowska — przejście przy cmentarzu'),
    ('13278522081', 'SL06_POWAZKOWSKA_KRASINSKIEGO', 'Powązkowska × Krasińskiego/Ficowskiego'),
    ('5022839623', 'SL07_POWAZKOWSKA_RYDYGIERA', 'Powązkowska × Rydygiera'),
    ('9972107244', 'SL08_POWAZKOWSKA_DUCHNICKA', 'Powązkowska × Duchnicka'),
    ('12593615866', 'SL09_POWAZKOWSKA_TATARSKA', 'Powązkowska × Tatarska'),
    ('3707287275', 'SL10_POWAZKOWSKA_OKOPOWA', 'Powązkowska × Okopowa'),
)


def local_xy(coordinate, origin):
    longitude, latitude = coordinate
    lon0, lat0 = origin
    return (
        EARTH_RADIUS_M * math.cos(math.radians(lat0)) * math.radians(longitude - lon0),
        EARTH_RADIUS_M * math.radians(latitude - lat0),
    )


def wgs84(point, origin):
    x, y = point
    lon0, lat0 = origin
    return [
        lon0 + math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(lat0)))),
        lat0 + math.degrees(y / EARTH_RADIUS_M),
    ]


def project(coordinates, coordinate):
    origin = coordinates[0]
    route_xy = [local_xy(value, origin) for value in coordinates]
    target = local_xy(coordinate, origin)
    cumulative = 0.0
    candidates = []
    for index, (first, second) in enumerate(zip(route_xy, route_xy[1:])):
        dx, dy = second[0] - first[0], second[1] - first[1]
        length_squared = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((target[0] - first[0]) * dx +
                                (target[1] - first[1]) * dy) / length_squared))
        point = first[0] + t * dx, first[1] + t * dy
        distance = math.dist(target, point)
        length = math.sqrt(length_squared)
        candidates.append((distance, index, cumulative + t * length, point, (dx / length, dy / length)))
        cumulative += length
    return min(candidates)


def load_osm(paths):
    nodes = {}
    ways = {}
    for path in paths:
        root = ET.parse(path).getroot()
        local_nodes = {
            node.attrib['id']: (
                float(node.attrib['lon']), float(node.attrib['lat']),
                {tag.attrib['k']: tag.attrib['v'] for tag in node.findall('tag')},
            )
            for node in root.findall('node')
        }
        nodes.update(local_nodes)
        for way in root.findall('way'):
            tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
            coordinates = [local_nodes[item.attrib['ref']][:2] for item in way.findall('nd')
                           if item.attrib['ref'] in local_nodes]
            if len(coordinates) >= 2:
                ways[way.attrib['id']] = (coordinates, tags)
    return nodes, ways


def build(osrm_path, osm_paths, route_output, map_output):
    osrm = json.loads(Path(osrm_path).read_text(encoding='utf-8'))
    if osrm.get('code') != 'Ok' or not osrm.get('routes'):
        raise ValueError('OSRM source does not contain a successful route')
    route_source = osrm['routes'][0]
    coordinates = route_source['geometry']['coordinates']
    route_length_m = sum(
        math.dist(local_xy(second, coordinates[0]), local_xy(first, coordinates[0]))
        for first, second in zip(coordinates, coordinates[1:])
    )
    nodes, ways = load_osm(osm_paths)

    stop_lines = []
    for node_id, stop_line_id, label in CONTROL_POINTS:
        if node_id not in nodes or nodes[node_id][2].get('highway') != 'traffic_signals':
            raise ValueError(f'Missing OSM traffic-signal node {node_id}')
        node_coordinate = nodes[node_id][:2]
        distance, segment_index, _, center, tangent = project(coordinates, node_coordinate)
        if distance > 20:
            raise ValueError(f'{stop_line_id} is {distance:.1f} m from routed carriageway')
        normal = -tangent[1], tangent[0]
        half_width_m = 12
        line = [
            wgs84((center[0] - normal[0] * half_width_m,
                   center[1] - normal[1] * half_width_m), coordinates[0]),
            wgs84((center[0] + normal[0] * half_width_m,
                   center[1] + normal[1] * half_width_m), coordinates[0]),
        ]
        stop_lines.append({
            'stop_line_id': stop_line_id,
            'signal_id': None,
            'segment_index': segment_index,
            'coordinates': line,
            'direction': 'FORWARD',
            'movement': 'STRAIGHT',
            'source': {
                'kind': 'OPENSTREETMAP_TRAFFIC_SIGNAL_NODE',
                'url': f'https://www.openstreetmap.org/node/{node_id}',
                'obtained_on': '2026-09-19',
                'label': label,
                'notes': 'Linia prostopadła do geometrii w pozycji węzła OSM; nie jest pomiarem terenowym.',
            },
            'verification': {
                'status': 'DRAFT',
                'date': '2026-09-19',
                'notes': 'Położenie i właściwy sygnalizator wymagają potwierdzenia przez pasażera.',
            },
            'position_uncertainty_m': 15,
        })

    route = {
        'schema_version': 1,
        'route_id': 'arkadia_maczka_okopowa_v1',
        'geometry_version': 'osm-osrm-desk-2026-09-19-v1',
        'name': 'Arkadia: Reymonta/Maczka → Powązkowska/Okopowa',
        'direction_description': (
            'Od świateł przy Reymonta/Maczka w kierunku wschodnim ulicą Maczka, '
            'następnie Powązkowską do świateł jazdy na wprost przez Okopową; '
            'pierwszy test kończy się przy McDonald’s, bez przedłużenia do ronda ONZ.'
        ),
        'coordinates': coordinates,
        'source': {
            'kind': 'OSRM_ROUTE_OVER_OPENSTREETMAP',
            'url': ('https://router.project-osrm.org/route/v1/driving/'
                    '20.932530,52.268550;20.981089,52.253278'),
            'obtained_on': '2026-09-19',
            'attribution': '© OpenStreetMap contributors, ODbL 1.0',
            'distance_m': route_source['distance'],
            'duration_seconds': route_source['duration'],
            'notes': 'Granice i kierunek podał użytkownik; przebieg sprawdzono biurkowo z OSM/OSRM.',
        },
        'geometry_verification': {
            'status': 'DESK_CHECKED',
            'date': '2026-09-19',
            'notes': 'Właściwa jezdnia i wszystkie połączenia wymagają odbioru podczas kontrolowanego przejazdu.',
        },
        'speed_sections': [{
            'start_s_m': 0,
            'end_s_m': route_length_m,
            'limit_mps': 50 / 3.6,
            'source': {
                'kind': 'OPENSTREETMAP_MAXSPEED',
                'url': 'https://www.openstreetmap.org/copyright',
                'obtained_on': '2026-09-19',
                'notes': 'Tag maxspeed=50 na odcinkach Maczka, ronda i Powązkowskiej; znaki wymagają kontroli terenowej.',
            },
            'verification': {
                'status': 'DESK_CHECKED',
                'date': '2026-09-19',
                'notes': 'Nie używać do rekomendacji live przed potwierdzeniem znaków w terenie.',
            },
        }],
        'stop_lines': stop_lines,
    }
    Path(route_output).write_text(json.dumps(route, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    features = []
    for way_id, (way_coordinates, tags) in ways.items():
        if tags.get('highway') not in ROAD_KINDS:
            continue
        features.append({
            'type': 'Feature',
            'properties': {
                'name': tags.get('name', ''),
                'kind': tags['highway'],
                'osm_way_id': way_id,
            },
            'geometry': {'type': 'LineString', 'coordinates': way_coordinates},
        })
    map_data = {
        'type': 'FeatureCollection',
        'features': features,
        'demo_route': [],
        'metadata': {
            'attribution': '© OpenStreetMap contributors',
            'license': 'ODbL 1.0',
            'copyright_url': 'https://www.openstreetmap.org/copyright',
            'source_url': 'https://api.openstreetmap.org/api/0.6/map',
            'extracted_on': date.today().isoformat(),
            'bbox': [20.928, 52.249, 20.985, 52.272],
            'marker_quality': 'DRAFT',
            'notes': 'Offline road extract for the Arkadia pilot; stop lines are stored in the route fixture.',
        },
    }
    Path(map_output).write_text(json.dumps(map_data, ensure_ascii=False, separators=(',', ':')) + '\n',
                                encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('osrm_json')
    parser.add_argument('route_output')
    parser.add_argument('map_output')
    parser.add_argument('osm_xml', nargs='+')
    args = parser.parse_args()
    build(args.osrm_json, args.osm_xml, args.route_output, args.map_output)


if __name__ == '__main__':
    main()
