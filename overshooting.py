#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
from compassbearing import calculate_initial_compass_bearing
import geopy
from geopy.distance import great_circle

class Cell(object):
    """docstring for Cell"""
    sector_degres = 50
    max_cells_in_sector = 5
    samples_percentage = 85
    max_l_ra_ta_ue_index = 12
    str_translation = [
                            '0 - 156 mts',
                            '156 - 234 mts',
                            '234 - 546 mts',
                            '546 - 1014 mts',
                            '1.01 - 1.9 Km',
                            '1.9 - 3.5 Km',
                            '3.5 - 6.6 Km',
                            '6.6 - 14.4 Km',
                            '14.4  - 30 Km',
                            '30 - 53 Km',
                            '53 - 76 Km',
                            '76.8 - ... Km',
                        ]
    num_translation = [
                            156,
                            234,
                            546,
                            1014,
                            1900,
                            3500,
                            6600,
                            14400,
                            30000,
                            53000,
                            76000,
                            100000,
                        ]

    def __init__(self,
        cellname=None,latitude=None,longitude=None,
            azimuth=None,comuna=None):
        super(Cell, self).__init__()
        self.cellname = cellname
        self.latitude = latitude
        self.longitude = longitude
        self.azimuth = azimuth
        self.comuna = comuna
        self.distance = None
        self.sector_average = 0.0
        self.initial_angle = None
        self.final_angle = None
        self.cells_between_angles = []
        self.ta = []
        self.ta_shortest_distance = None

    def set_distance(self,cell=None):
        start = (self.latitude, self.longitude)
        end = (cell.latitude, cell.longitude)
        d = great_circle(start, end).meters
        self.distance = int(d)
        # print(f'set_distance: ({cell.cellname} - {self.cellname}) = {self.distance}') # debug

    def get_distance(self):
        return self.distance

    def set_ta_shortest_distance(self):
        total = 0.0
        for value in self.ta:
            total += value
        parcial_percentage = int(total * Cell.samples_percentage / 100)

        parcial = 0.0
        self.ta_shortest_distance = None
        for i, value in enumerate(self.ta):
            parcial += value
            if parcial >= parcial_percentage:
                self.ta_shortest_distance = i
                break

def read_lcellreference(file='./data/lcellreference_v2.csv',delimiter=','):
    '''
    It returns a list of Cell objects
    '''
    cells = []

    dict_ = {}
    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                dict_ = {f:i for i,f in enumerate(row)}
                # print(f"\tCELLNAME\tLON\t\tLAT\tAZIMUTH") # debug
            else:
                cellname = row[dict_['CELLNAME']]
                lat = float(row[dict_['LAT']])
                lon = float(row[dict_['LON']])
                azimuth = int(row[dict_['AZIMUTH']])
                comuna = row[dict_['COMUNA']]
                cell = Cell(cellname=cellname,latitude=lat,longitude=lon,
                            azimuth=azimuth,comuna=comuna)
                cell.initial_angle = (cell.azimuth - Cell.sector_degres) % 360
                cell.final_angle = (cell.azimuth + Cell.sector_degres) % 360
                # print(f'cellname={cellname} lat={lat} lon={lon} '
                #     f'azimuth={azimuth} '
                #     f'initial_angle={cell.initial_angle} '
                #     f'final_angle={cell.final_angle} '
                #     ) # debug
                cells.append(cell)
            line_count += 1
        # print(f'read_lcellreference: processed {line_count} lines.') # debug

    return cells

def read_prs_lte_hour(file='./data/prs_lte_hour_2020_12_02_v2.csv',
                                                    delimiter=','):
    '''
    It returns a dictionary with elements like:
        key = cellname
        data = [L_RA_TA_UE_Index, ..., L_RA_TA_UE_Index11]
    '''
    counters = {}

    dict_ = {}
    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                dict_ = {f:i for i,f in enumerate(row)}
            else:
                values = []
                cellname = row[dict_['Cell_Name']]
                for i in range(Cell.max_l_ra_ta_ue_index):
                    column = 'L_RA_TA_UE_Index' + str(i)
                    value = int(row[dict_[column]])
                    values.append(value)
                counters[cellname] = values
            line_count += 1
        # print(f'read_prs_lte_hour: processed {line_count} lines.') # debug

    return counters

if __name__ == '__main__':
    # create cells list
    cells = read_lcellreference()
    print(f'main: cells has {len(cells)} elements.', flush=True) # debug

    # detect cell's cells_between_angles
    # Nota:
    # Son aproximadamente 20.000 celdas --> 400 millones de comparaciones.
    # Toma 11 minutos en mi máquina.
    # Optimización posible, comparar sólo entre celdas de la misma comuna.
    # Con esto baja a 72 segundos
    for pivot in cells:
        for cell in cells:
            if pivot.cellname == cell.cellname:
                continue
            if pivot.comuna != cell.comuna:
                continue
            pointA = (pivot.latitude, pivot.longitude)
            pointB = (cell.latitude, cell.longitude)
            bearing = calculate_initial_compass_bearing(pointA, pointB)
            if bearing >= pivot.initial_angle and bearing <= pivot.final_angle:
                pivot.cells_between_angles.append(cell)
    print(f"main: cells_between_angles detected", flush=True) # debug

    # prune cell's cells_between_angles
    # aquí voy: debo calcular distancia media para cells_between_angles
    for pivot in cells:
        if not pivot.cells_between_angles:
            continue
        for cell in pivot.cells_between_angles:
            cell.set_distance(cell=pivot)
        ordered = sorted(pivot.cells_between_angles, key=Cell.get_distance)
        pivot.cells_between_angles = []
        count = 0
        for cell in ordered:
            if count >= Cell.max_cells_in_sector:
                break
            pivot.cells_between_angles.append(cell)
            count += 1
        # sector_average
        total = 0.0
        for cell in pivot.cells_between_angles:
            total += cell.distance
        pivot.sector_average = total/len(pivot.cells_between_angles)

    print(f"main: distance in cells_between_angles set", flush=True) # debug
    print(f"main: cells in cells_between_angles ordered", flush=True) # debug
    print(f"main: cells in cells_between_angles pruned", flush=True) # debug
    print(f"main: sector_average in cells_between_angles set", flush=True) # debug

    # create counters dictionary
    counters = read_prs_lte_hour()
    print(f"main: counters dictionary created", flush=True) # debug

    # add time advanced counters to cells
    for cell in cells:
        cell.ta = counters.get(cell.cellname, [])
    print(f"main: time advanced counters added", flush=True) # debug

    # calculate shortest distance for samples_percentage
    for cell in cells:
        cell.set_ta_shortest_distance()
    print(f"main: shortest distance for samples_percentage calculated",
        flush=True) # debug

    # detect overshooting
    for cell in cells:
        if not cell.ta_shortest_distance:
            # print(f'{cell.cellname} not found in prs_lte_hour data source')
            continue
        if cell.sector_average > Cell.num_translation[cell.ta_shortest_distance]:
            print(f'{cell.cellname} overshooting [{Cell.str_translation[cell.ta_shortest_distance]}]')
    print(f"main: overshooting detected", flush=True) # debug
