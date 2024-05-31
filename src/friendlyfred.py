import json
import urllib3
from tqdm import tqdm
from lxml import etree
import pandas as pd
from anytree import Node, RenderTree
from categories import categories


API_KEY = '8c1eb4cddd303e092cfc0941ad56e599'
FILE_TYPE = 'json'
http = urllib3.PoolManager()


def _save_categories(categories):
    '''Save the categories dictionary to a file.'''
    with open('categories.py', 'w') as f:
        f.write('categories = ' + str(categories) + '\n')
    return None


def get_categories():
    """Return the categories from saved dictionary."""
    from categories import categories
    return categories


def extract_attributes(dictionary):
    '''Extract the name, id, and parent_id from a dictionary.'''
    name = dictionary['name']
    id = dictionary['id']
    parent_id = dictionary['parent_id']
    return name, id, parent_id


def _get_category_id(category):
    '''Get the category_id from the category name or category_id iterating over categories dict.'''
    if isinstance(category, int):
        category_id = category
    elif isinstance(category, str):
        categories = get_categories()
        try:
            category_id = __get_category_id_by_name_recursive(categories, category)
        except KeyError:
            print(f'Category "{category}" not found.')
            return None
    return category_id


def __get_category_id_by_name_recursive(search_dict, search_key):
    """Takes a nested dict, and searches all dicts for a key and returns the value['id'].
    
    Parameters:
    search_dict: dict
        The dictionary to search.
    search_key: str
        The key to search for.
        
    Returns:
    value: The value of the search_key.
    
    """
    for key, value in search_dict.items():
        if key == search_key:
            return value['id']
        if isinstance(value, dict):
            id = __get_category_id_by_name_recursive(value, search_key)
            if id is not None:
                return id


def _get_category_name(id):
    '''Get the category name from the category_id iterating over categories dict.'''
    categories = get_categories()
    try:
        category_name = __get_category_name_by_id_recursive(categories, id)
    except KeyError:
        print(f'Category_id "{id}" not found.')
        return None
    return category_name


def __get_category_name_by_id_recursive(search_dict, search_key):
    """Takes a nested dict, and searches all dicts, if dict['id'] == search_key, return parent key of this dict.
    
    Parameters:
    search_dict: dict
        The dictionary to search.
    search_key: int
        The key to search for.
    
    Returns:
    value: The value of the search_key.

    """
    for key, value in search_dict.items():
        if isinstance(value, dict):
            if 'id' in value:
                if value['id'] == search_key:
                    return key
            name = __get_category_name_by_id_recursive(value, search_key)
            if name is not None:
                return name


def _get_dict_value_by_key_recursive(search_dict, search_key):
    """Takes a nested dict, and searches all dicts for a key and returns the value.
    
    Parameters:
    search_dict: dict
        The dictionary to search.
    search_key: str
        The key to search for.
        
    Returns:
    value: dict
        The value of the search_key.
    
    """
    for key, value in search_dict.items():
        if key == search_key:
            return value
        if isinstance(value, dict):
            results = _get_dict_value_by_key_recursive(value, search_key)
            if results is not None:
                return results        

def get_children(category):
    '''Query FRED for the children of a category and return a dictionary with the children data.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
        
    Returns:
    dict: The category data.
    
    '''
    if isinstance(category, str):
        category_id = _get_category_id(category)
    else:
        category_id = category
    url = f'https://api.stlouisfed.org/fred/category/children?category_id={category_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    children = {}
    for child in response['categories']:
        name, id, parent_id = extract_attributes(child)
        children[name] = {'id': id, 'parent_id': parent_id}
    if not children:
        print(f'No subcategories found for category: {category}')
    return children


def get_category(category):
    '''Query FRED for the category data and return a dictionary with the category data.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
        
    Returns:
    dict: The category data.
    
    '''
    category_id = _get_category_id(category)
    url = f'https://api.stlouisfed.org/fred/category?category_id={category_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    return response


def _find_parents(data, category_name, parents=[]):
    '''Find the parents of a target key in a nested dictionary.
    '''
    for key, value in data.items():
        new_path = parents + [key]
        if key == category_name:
            return new_path[:-1]
        if isinstance(value, dict):
            result = _find_parents(value, category_name, new_path)
            if result:
                return result
    return None


def _create_tree_for_category(category):
    root_node_name = 'root'
    category_dict = _get_dict_value_by_key_recursive(categories, category)
    if category_dict is None:
        return None
    parents = _find_parents(categories, category)
    parents = [x for x in parents if x != 'children']
    parents.append(category)
    top_level = Node(root_node_name)
    for ix, parent in enumerate(parents):
        if ix == 0:
            node = Node(parent, parent=top_level)
        else:
            node = Node(parent, parent=node)
    try:
        for subcat in category_dict['children'].keys():
            last_node = Node(subcat, parent=node)
    except KeyError:
        subcat = 'series: [get series meta: get_series_in_category(category), get series observations: get_observations(series_id)]'
        last_node = Node(subcat, parent=node)
    if 'children' in category_dict:
        if not category_dict['children']:
            subcat = 'series: [get series meta: get_series_in_category(category), get series observations: get_observations(series_id)]'
            last_node = Node(subcat, parent=node)
    return top_level    


def _print_etree(tree, highlight_category = None):
    '''Print a lxml.tree.'''
    CSI = "\x1B\x5B"
    for pre, fill, node in RenderTree(tree):
        if highlight_category is not None:
            if node.name == highlight_category:
                print(f'{CSI}30;42m{pre}{node.name}{CSI}0m')
            else:
                print(f'{pre}{node.name}')
        else:
            print(f'{pre}{node.name}')


def print_tree(depth = 0, category = None):
    '''Print all available FRED categories.
    
    Parameters:
    depth: int
        The depth of the categories to print. Can take values from 0 to 2.
    category: str or int
        The category_title or category_id.

    If category is passed, the function will print the category and its subcategories, 
    in this case it will disregard the depth parameter.

    Returns:
    None
        
    '''
    root_node_name = 'root'
    if category is not None:
        if isinstance(category, int):
            category = _get_category_name(category)
        top_level = _create_tree_for_category(category)
        if top_level is None:
            print(f'Category {category} not found, please refer to .print_tree(depth = 2) for all available categories.')
            return None
        series_names = _get_series_names_for_category(category)
        if series_names is not None:
            last_node = _get_last_tree_node(top_level)  
            for series_name in series_names:
                top_level = _add_node_to_parent(top_level, last_node, series_name)
    else:
        top_level = Node(root_node_name)
        top_level.name
        for top_cat, subcats in categories.items():
            top_cat_node = Node(top_cat, parent=top_level)
            subcats_dict = subcats['children'] if 'children' in subcats else subcats
            if depth == 1:
                for subcat, id in subcats_dict.items():
                    subcat_node = Node(subcat, parent=top_cat_node)
            elif depth > 1:
                for subcat, id in subcats_dict.items():
                    subcat_node = Node(subcat, parent=top_cat_node)
                    for subsubcat, id in subcats_dict[subcat]['children'].items():
                        subsubcat_node = Node(subsubcat, parent=subcat_node)
    if category is not None:
        _print_etree(top_level, highlight_category = category)
        if category is None and depth < 2:
            print(f'\nFor more details call get_categories(depth = {depth + 1})')
    else:
        _print_etree(top_level)
        if category is None and depth < 2:
            print(f'\nFor more details call get_categories(depth = {depth + 1})')
 

def update_categories():
    '''Update the categories dictionary with the latest categories from the FRED website.'''    
    print('Updating categories from FRED website. This may take about 60 seconds.')
    try:
        url = 'https://fred.stlouisfed.org/categories/'
        response = http.request('GET', url)
        response = response.data.decode('utf-8')
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(response, parser)
        categories = {}
        groups = root.xpath('//div[@class="fred-categories-group"]')
        for group in groups:
            group = etree.tostring(group)
            group = group.split(b'<br class="clear">')[0]
            group = etree.fromstring(group, parser)
            parent = group.xpath('//p[@class="large fred-categories-parent"]')
            parent_id = parent[0].xpath('a/@href')
            parent_id = int(parent_id[0].split('/')[-1])
            parent_name = parent[0].xpath('a/strong/text()')[0]
            parent_name = parent_name.replace('  ', ' & ')
            children = group.xpath('//p[@class="fred-categories-children"]/span')
            children_ids = [child.xpath('a/@href')[0] for child in children]
            children_ids = [int(child.split('/')[-1]) for child in children_ids]
            children_names = [child.xpath('a/text()')[0] for child in children]
            children_names = [child.replace('  ', ' & ') for child in children_names]
            categories[parent_name] = {'id': parent_id, 'parent_id':0, 'children': {}}
            categories[parent_name]['children'] = {}
            for ix, id in enumerate(children_ids):
                categories[parent_name]['children'][children_names[ix]] = {'id': id, 'parent_id': parent_id}
        for parent_name, children in tqdm(categories.items()):
            for child_name, child in children['children'].items():
                child_id = child['id']
                child['children'] = get_children(child_id)
        _save_categories(categories)
        return categories
    except Exception as e:
        print(f'Error updating categories: {e}')
        print('\nReturning initial categories.')
        return get_categories()


def get_series_in_category(category, discontinued = True):
    '''Get the series in a category.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
    discontinued: bool
        If False exclude series which have "(DISCONTINUED)" string in title. Default is True.
        
    Returns:
    pd.DataFrame: df with metadata of all the series in category.
    
    '''
    category_id = _get_category_id(category)
    url = f'https://api.stlouisfed.org/fred/category/series?category_id={category_id}&realtime_start=1777-04-04'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    response = response['seriess']
    response = pd.DataFrame(response)
    if not discontinued:
        response = response[~response['title'].str.contains('DISCONTINUED')]
    return response

def get_observations(series_id):
    '''Get the observations in a series.
    
    Parameters:
    series: str or int
        The series name or series_id to query.
        
    Returns:
    dict: The observations in the series.
    
    '''
    url = f'https://api.stlouisfed.org/fred/series/observations?series_id={series_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    try:
        response = response['observations']
    except KeyError:
        print(response)
        return None
    observations = {}
    for observation in response:
        observations[observation['date']] = observation['value']
    # make pandas df
    observations = pd.DataFrame.from_dict(observations, orient='index', columns=['value'])
    return observations


def _get_last_tree_node(tree):
    '''Get the last node in a tree.'''
    for pre, fill, node in RenderTree(tree):
        pass
    return node


def _delete_last_tree_node(tree):
    '''Delete the last node in a tree.'''
    for pre, fill, node in RenderTree(tree):
        pass
    node.parent = None
    return tree


def _add_node_to_parent(tree, parent, new_node_name):
    '''Add a node to a parent node in a tree.'''
    for pre, fill, node in RenderTree(tree):
        if node == parent:
            new_node = Node(new_node_name, parent=node)
    return tree


def _get_series_names_for_category(category, discontinued = True):
    series_data = get_series_in_category(category)
    if series_data.empty:
        print(f'No series found for category "{category}". Wrong category name or category contains subcategories.')
        return None
    series_names = [f"{val} || series_id: {key}" for key, val in  dict(zip(series_data['id'], series_data['title'])).items()]
    if not discontinued:
        series_names = [s for s in series_names if "(DISCONTINUED)" not in s]
    return series_names


def print_series_in_category(category, discontinued = True):
    '''Print the series in a category.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
    exclude_discontinued: bool
        Exclude series which have "(DISCONTINUED)" string in title
    
    Returns:
    None
    
    '''
    if isinstance(category, int):
        category = _get_category_name(category)
    category_tree = _create_tree_for_category(category)

    if category_tree is None:
        print(f'Category {category} not found, please refer to .print_tree(depth = 2) for all available categories.')
        return None
    last_node = _get_last_tree_node(category_tree)
    if last_node.name.startswith('series:'):
        category_tree = _delete_last_tree_node(category_tree)
    series_names = _get_series_names_for_category(category, discontinued = True)
    if series_names is not None:
        last_node = _get_last_tree_node(category_tree)
        for series_name in series_names:
            category_tree = _add_node_to_parent(category_tree, last_node, series_name)
    _print_etree(category_tree, highlight_category = category)
    return None


def _search_recursive(string, categories=categories, results=None):
    '''Search for a category by iterating over all categories and checking if string is contained in category name text.'''
    if results is None:
        results = []
    for key, value in categories.items():
        if string.lower() in key.lower():
            results.append(key)
        if isinstance(value, dict):
            _search_recursive(string, value, results)
    return results


def search(string):
    results = _search_recursive(string)
    if results:
        print(f'Found {len(results)} matching categories for search term "{string}":')
        for result in results:
            print(f'"{result}"')
        print('\nDive deeper by using methods: \n.print_category(name)\n.print_series_in_category(name)\n.get_series_in_category(name)\n.get_observations(series_id)')
    else:
        print(f'Found no matching categories for search term "{string}"')
    return results


print_tree(depth=0)
print_tree(depth=1) 
print_tree(depth=2)

print_tree(category = 'National Income & Product Accounts')
print_tree(category = 'Money Market Accounts')
print_tree(category = 'Weekly Initial Claims')
print_tree(category = 22)

# !!!!! FIX: both below return the same output. Maybe scrap print_series_in_category
# !!!!! Keep in mind the discontinued arg, not present in print_tree yet
print_tree(category = 33058)
print_series_in_category(category = 33058, discontinued=False)

print_series_in_category(category = 33058, discontinued=True)
print_series_in_category(category = 'Weekly Initial Claims')
print_series_in_category(category = '4-Week Moving Average of Continued Claims (Insured Unemployment)') # should not print series
print_series_in_category(category = 'National Income & Product Accounts')
print_tree(category = 'National Income & Product Accounts')
print_series_in_category(category = 'Interest Rates')
get_observations('OBMMIC30YFLVLE80FLT680')
categories = get_categories()
get_category(117)
get_category('Prime Bank Loan Rate')
get_children('Interest Rates')
get_children(22)
get_children(34009) # should return no children
get_children('AMERIBOR Benchmark Rates') # should return no children
get_series_in_category('Kosovo')
get_series_in_category('Kosovo', discontinued=False)
get_observations('ALKSVA052SCEN')
get_observations('ALKSVA05N') # should return error message
'''
TODO: 
add arguments to all functions
add all other methods
implement search as per API
chage get_categories to query the categories dict
'''

results = search('stock')
save = series_in_cat.copy()
