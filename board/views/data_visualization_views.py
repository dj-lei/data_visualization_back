from board.views import *


def logic_test_data(data, RSW_Monitor_node):
    level = list(RSW_Monitor_node.Level.values)
    rel = {}
    rel_flag = {}
    # height = 10000
    width = 200
    width_clearance = 50
    height_clearance = 10
    RSW_Monitor_node['height'] = 0
    RSW_Monitor_node['width'] = width - width_clearance
    RSW_Monitor_node['location_x'] = 0
    RSW_Monitor_node['location_y'] = 0
    tmp = []

    for i in set(level):
        rel[str(i)] = level.count(i)
        tmp.append(level.count(i))
        rel_flag[str(i)] = 0
    height = max(tmp) * (50 + height_clearance)

    for i, level in enumerate(RSW_Monitor_node.Level.values):
        RSW_Monitor_node.loc[i, 'height'] = int(height / rel[str(level)]) - height_clearance
        RSW_Monitor_node.loc[i, 'location_x'] = level * width * 2

        num = rel_flag[str(level)]
        RSW_Monitor_node.loc[i, 'location_y'] = num * int(height / rel[str(level)])
        rel_flag[str(level)] = rel_flag[str(level)] + 1

    nodes = []
    for node,level,desc,height,width,location_x,location_y in RSW_Monitor_node.values:
        nodes.append({'id': node, 'desc': desc, 'height': height, 'width': width, 'location_x': location_x, 'location_y': location_y})

    links = []
    for rel, source, target in data[['type', 'source', 'target']].values:
        links.append({'source': source, 'target': target, 'type': rel})

    types = list(set(data['type'].values))
    return {'nodes': nodes, 'links': links, 'types': types}


def physical_topology(components, components_desc, layer_ref):
    nodes = []
    for key in components.keys():
        if (components[key]['layerRef'] == layer_ref) & (len(components[key]['pins']) > 2):
            nodes.append({'id': key, 'location_x': components[key]['startLocation']['x'],
                           'location_y': components[key]['startLocation']['y'],
                           'width': components[key]['packageValue']['width'],
                           'height': components[key]['packageValue']['height'],
                           'desc': components_desc[key] if key in components_desc.keys() else 'No description'})
    return {'nodes': nodes}


def is_filtered_pin(net):
    if 'GND' in net:
        return True
    elif 'VDD' in net:
        return True
    elif 'VCC' in net:
        return True
    elif len(re.findall('\d+V\d+', net)) > 0:
        return True
    return False


def find_unfiltered_component(component, components, filtered_components, logical_nets, result, rels, level,
                              source_component_name, source_component_pin, source_component_net, visited_nets,
                              delete_elms):
    if component not in components.keys():
        delete_elms.append({'level': level, 'name': component})
        return -1

    for pin in components[component]['pins']:
        if (pin['net'] not in visited_nets) & (is_filtered_pin(pin['net']) == False):
            visited_nets.add(pin['net'])

            if component == source_component_name:
                source_component_pin = pin['pin']
                source_component_net = pin['net']

            for component_pin in logical_nets[pin['net']]:
                if component_pin['componentRef'] in filtered_components.keys():
                    find_unfiltered_component(component_pin['componentRef'], components, filtered_components,
                                              logical_nets, result, rels, level, source_component_name,
                                              source_component_pin, source_component_net, visited_nets, delete_elms)
                else:
                    if component_pin['componentRef'] != source_component_name:
                        if component_pin['componentRef'] not in result[level].keys():
                            if component_pin['componentRef'] not in result[level + 1].keys():
                                result[level + 1][component_pin['componentRef']] = []

                        if source_component_name + '#' + component_pin['componentRef'] not in rels:
                            rels[source_component_name + '#' + component_pin['componentRef']] = []
                        tmp = source_component_name + '#' + source_component_pin + '#' + source_component_net + ':' + \
                              component_pin['componentRef'] + '#' + component_pin['pin'] + '#' + pin['net']
                        rels[source_component_name + '#' + component_pin['componentRef']].append(tmp)


def parse_logic_topology(visual_angle_entrance):
    result = [{} for i in range(0, 100)]
    result[0][visual_angle_entrance] = []
    rels = {}
    delete_elms = []
    visited_nets = set()

    for level, _ in enumerate(result):
        if len(result[level].keys()) == 0:
            break

        for key in result[level].keys():
            find_unfiltered_component(key, components, filtered_components, logical_nets, result, rels,
                                      level, key, '', '', visited_nets, delete_elms)

    for elm in delete_elms:
        result[elm['level']].pop(elm['name'])
        tmp = []
        for key in rels.keys():
            if elm['name'] == key.split('#')[1]:
                tmp.append(key)

        for key in tmp:
            rels.pop(key)
    ###############################################
    levels = []
    for level, _ in enumerate(result):
        if len(result[level].keys()) == 0:
            break

        for key in result[level]:
            levels.append({'Node': key, 'Level': level,
                           'Desc': components_desc[key] if key in components_desc.keys() else 'No description'})

    nodes = []
    for key in rels.keys():
        nodes.append({'source':key.split('#')[0], 'target':key.split('#')[1], 'type':' '.join(rels[key]), 'count':len(rels[key])})
    return levels, nodes


def filter_by_nodes(levels, rels, filter_nodes, filter_rels):
    ret_levels = []
    ret_rels = []
    tmp = []
    for item in levels:
        for word in filter_nodes:
            if word.lower() in item['Desc'].lower():
                ret_levels.append(item)
                tmp.append(item['Node'])

    for item in rels:
        if (item['source'] in tmp) & (item['target'] in tmp):
            temp = []
            for rel in item['type'].split(' '):
                for k in filter_rels:
                    if k.lower() in rel.lower():
                        temp.append(rel)
            item['type'] = ' '.join(temp)
            ret_rels.append(item)
    return ret_levels, ret_rels


def auto_clusters_layered(visual_angle_entrance, filter_levels, filter_rels, n_clusters):
    n_clusters = n_clusters - 1
    ret = []
    x = []
    for item in filter_rels:
        if item['source'] == visual_angle_entrance:
            ret.append(item)
            x.append([item['count']])

    clf = KMeans(n_clusters=n_clusters)
    clf.fit(x)

    original_centers = clf.cluster_centers_
    labels = clf.labels_
    sorted_centers = sorted(original_centers)
    sorted_centers.reverse()

    clusters_nodes = []
    for node in filter_levels:
        if node['Node'] == visual_angle_entrance:
            clusters_nodes.append(node)
            continue

        for i, item in enumerate(filter_rels):
            if (item['source'] == visual_angle_entrance) & (item['target'] == node['Node']):
                predict_value = original_centers[labels[i]][0]
                for j, v in enumerate(sorted_centers):
                    if v == predict_value:
                        node['Level'] = j + 1
                        clusters_nodes.append(node)
    return clusters_nodes


def get(request):
    try:
        if request.method == 'GET':
            operate = request.GET.get(cf['DATA_VISUALIZATION']['OPERATE'])

            if operate == cf['DATA_VISUALIZATION']['GET_TEST_DATA']:
                data = pd.read_excel("D:\\projects\\test\\RSW_Monitor.xlsx")
                RSW_Monitor_node = pd.read_excel("D:\\projects\\test\\RSW_Monitor_node.xlsx")
                return JsonResponse({'content': logic_test_data(data, RSW_Monitor_node)})
            elif operate == cf['DATA_VISUALIZATION']['GET_LOGIC_CHART_DATA']:
                visual_angle_entrance = 'D2CMIB'
                levels, nodes = parse_logic_topology(visual_angle_entrance)
                return JsonResponse({'content': logic_test_data(pd.DataFrame(nodes), pd.DataFrame(levels))})
            elif operate == cf['DATA_VISUALIZATION']['GET_LOGIC_CHART_DATA_FILTER_BY_NODES']:
                filter_nodes = request.GET.get(cf['DATA_VISUALIZATION']['FILTER_NODES']).split(',')
                filter_rels = request.GET.get(cf['DATA_VISUALIZATION']['FILTER_RELS']).split(',')
                n_clusters = int(request.GET.get(cf['DATA_VISUALIZATION']['N_CLUSTERS']))

                visual_angle_entrance = 'D2CMIB'
                levels, nodes = parse_logic_topology(visual_angle_entrance)
                levels, nodes = filter_by_nodes(levels, nodes, filter_nodes, filter_rels)
                if n_clusters > 0:
                    levels = auto_clusters_layered(visual_angle_entrance, levels, nodes, n_clusters)
                return JsonResponse({'content': logic_test_data(pd.DataFrame(nodes), pd.DataFrame(levels))})
            elif operate == cf['DATA_VISUALIZATION']['GET_PHYSICS_CHART_DATA']:
                layer_ref = request.GET.get(cf['DATA_VISUALIZATION']['LAYER_REF'])
                return JsonResponse({'content': physical_topology(components, components_desc, layer_ref)})
            elif operate == cf['DATA_VISUALIZATION']['GET_ECHART_TEST_DATA']:
                return JsonResponse({'content': {'radon rxpwr': random.randint(0, 10), 'radon ipwr': random.randint(5, 20), 'radon wpwr': random.randint(10, 15)}})
        return HttpResponse(404)
    except Exception as e:
        traceback.print_exc()
