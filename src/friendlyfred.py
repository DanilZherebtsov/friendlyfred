import sys
import json
import pandas as pd
from lxml import etree
from tqdm import tqdm
from urllib3 import PoolManager
from anytree import Node, RenderTree
from categories import categories

http = PoolManager()

FILE_TYPE = 'json'
with open('../api_key.txt', 'r') as f:
    API_KEY = f.read()

ROOT_URL = 'https://api.stlouisfed.org/fred'


def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor


def _save_categories(categories):
    '''Save the categories dictionary to a file.'''
    with open('categories.py', 'w') as f:
        f.write('categories = ' + str(categories) + '\n')
    return None


def update_categories():
    '''Update the categories dictionary with the latest categories from the FRED website.'''    
    print('Updating categories from FRED website. This may take about 60 seconds.')
    try:
        url = f'https://fred.stlouisfed.org/categories/'
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
                child['children'] = get_subcategories(child_id)
        _save_categories(categories)
        return categories
    except Exception as e:
        print(f'Error updating categories: {e}')
        print('\nReturning initial categories.')
        return get_categories()


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


def get_categories():
    """Return categories from saved dictionary. 
    They reflect all categories and subcategories in FRED database."""
    from categories import categories
    return categories


def extract_attributes(dictionary):
    '''Extract the name, id, and parent_id from a dictionary.'''
    name = dictionary['name']
    id = dictionary['id']
    parent_id = dictionary['parent_id']
    return name, id, parent_id


def get_subcategories(category):
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
    url = f'{ROOT_URL}/category/children?category_id={category_id}'
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


def get_category_meta(category):
    '''Get category_id, name and parent_id.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
        
    Returns:
    dict: Category data.
    
    '''
    category_id = _get_category_id(category)
    url = f'{ROOT_URL}/category?category_id={category_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    return response


def get_related_categories(category):
    '''Get related categories for a category.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
    
    Returns:
    list: List of related categories.
    
    '''
    category_id = _get_category_id(category)
    url = f'{ROOT_URL}/category/related?category_id={category_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = _fetch_response(url)
    if 'error_code' in response:
        print(response['error_message'])
        return
    if not response['categories']:
        print(f'No related categories found for category: {category}')
        return
    return response['categories']
    

def get_series_meta(series_id):
    url = f'{ROOT_URL}/series?series_id={series_id}&api_key={API_KEY}&file_type={FILE_TYPE}'
    response = _fetch_response(url)
    series_meta = response['seriess']
    return series_meta


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


def _find_parents(data, category_name, parents=[]):
    '''Find the parents of a target key in a nested dictionary.'''
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
    '''Create a tree for a category and its subcategories.'''
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


def _print_anytree(tree, highlight_category = None):
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


def print_tree(depth = 0, category = None, discontinued = True):
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
                if not discontinued:
                    if "(DISCONTINUED)" in series_name:
                        continue
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
        _print_anytree(top_level, highlight_category = category)
        if category is None and depth < 2:
            print(f'\nFor more details call get_categories(depth = {depth + 1})')
    else:
        _print_anytree(top_level)
        if category is None and depth < 2:
            print(f'\nFor more details call get_categories(depth = {depth + 1})')


def _fetch_response(url):
    response = http.request('GET', url)
    response = json.loads(response.data.decode('utf-8'))
    return response


def get_observations(series_id, observation_start = "1776-07-04", observation_end = "9999-12-31", frequency = None):
    '''
    Get the datapoints in a series.

    Parameters:
    series_id: str
        series_id to query.
    observation_start: str
        The start date for the observations. Default is "1776-07-04". 
        Start date cannot be earlier than Default.
    observation_end: str
        The end date for the observations. Default is "9999-12-31".
    frequency: str
        The frequency of the observations. Default is None.

        Frequencies without period descriptions:

        d = Daily
        w = Weekly
        bw = Biweekly
        m = Monthly
        q = Quarterly
        sa = Semiannual
        a = Annual

        Frequencies with period descriptions:

        wef = Weekly, Ending Friday
        weth = Weekly, Ending Thursday
        wew = Weekly, Ending Wednesday
        wetu = Weekly, Ending Tuesday
        wem = Weekly, Ending Monday
        wesu = Weekly, Ending Sunday
        wesa = Weekly, Ending Saturday
        bwew = Biweekly, Ending Wednesday
        bwem = Biweekly, Ending Monday
    
    Returns:
    pd.DataFrame: df with dates and observations.

    '''
    frequency_values = ['d', 'w', 'bw', 'm', 'q', 'sa', 'a', 'wef', 'weth', 'wew', 'wetu', 'wem', 'wesu', 'wesa', 'bwew', 'bwem']
    url = f"{ROOT_URL}/series/observations?series_id={series_id}"
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    url = f'{url}&observation_start={observation_start}'
    url = f'{url}&observation_end={observation_end}'
    if frequency and frequency in frequency_values:
        url = f'{url}&frequency={frequency}'
    response = _fetch_response(url)
    if 'error_code' in response:
        print(response['error_message'])
        return
    data = pd.DataFrame(response['observations'])
    data = data[['date', 'value']]
    return data


def _construct_search_query(search_text):
    '''Construct a html search query from a search text.'''
    search_lst = [val.lower() for val in search_text.split(' ')]
    search_query = '+'.join(search_lst)
    search_query = search_query.replace('&', '')
    return search_query


def _add_order_by(url, order_by):
    '''Handle order_by parameter for search.
    
    Parameters:
    url: str
        The url to query.
    order_by: str

    Can handle urls from search and get_series_in_category functions.

    Returns:
    str: The url with the order_by parameter added.
    
    '''
    search_order_by_options = ['search_rank', 'series_id', 'title', 'units', 'frequency', 
                               'seasonal_adjustment', 'realtime_start', 'realtime_end', 
                               'last_updated', 'observation_start', 'observation_end', 
                               'popularity', 'group_popularity']
    
    get_series_in_category_order_by_options = ['series_id', 'title', 'units', 'frequency', 
                                               'seasonal_adjustment', 'realtime_start', 
                                               'realtime_end', 'last_updated', 'observation_start', 
                                               'observation_end', 'popularity', 'group_popularity']
    
    if 'search' in url:
        order_by_options = search_order_by_options
    else:
        order_by_options = get_series_in_category_order_by_options
    if order_by in order_by_options:
        url = f'{url}&order_by={order_by}'
    return url


def _add_sort_order(url, sort_order):
    '''Handle sort_order parameter for search.'''
    if sort_order in ['asc', 'desc']:
        url = f'{url}&sort_order={sort_order}'
    return url


def _add_filter(url, filter):
    '''Handle filter parameter for search.'''
    if filter is not None:    
        if len(filter) == 2:
            if filter[0] in ['frequency', 'units', 'seasonal_adjustment']:
                url = f'{url}&filter_variable={filter[0]}&filter_value={filter[1]}'
    return url


def search(search_text, discontinued = True, limit = 1000, order_by = 'search_rank', sort_order = 'asc', filter = None):
    '''Search for series in FRED database.
    
    Parameters:
    search_text: str
        Search query.
    limit: int
        Limit the number of results. Default is 1000. 
    order_by: str
        Order results by values of the specified attribute.
        One of the following strings: 'series_id', 'title', 'units', 'frequency', 
            'seasonal_adjustment', 'realtime_start', 'realtime_end', 'last_updated', 
            'observation_start', 'observation_end', 'popularity', 'group_popularity'.
        Default: search_rank
    sort_order: str
        Sort results is ascending or descending order for attribute values specified by order_by.
        One of the following strings: 'asc', 'desc'.
        Default: asc
    filter: tuple
        Filter results by values of the specified attribute.
        Two item tuple: (filter_variable, filter_value)
        One of the following strings: 'frequency', 'units', 'seasonal_adjustment'.
        Default: None
        Example: ('seasonal_adjustment', 'Not Seasonally Adjusted')

    FRED API returns a maximum of 1000 results per request. Some queries contain more 
    than 1000 results. In such cases, the function will make multiple requests to get all the results.
    Just pass the desired "limit" value.
        
    Returns:
    pd.DataFrame: df with metadata of all the series in category.
    
    '''
    max_results_per_request = 1000
    search_query = _construct_search_query(search_text)
    url = f'{ROOT_URL}/series/search?search_text={search_query}&api_key={API_KEY}&file_type={FILE_TYPE}'
    url = _add_order_by(url, order_by)
    url = _add_sort_order(url, sort_order)
    url = _add_filter(url, filter)
    response = _fetch_response(url)
    if 'error_code' in response:
        print(response['error_message'])
        return
    data = pd.DataFrame(response['seriess'])
    if (len(data) < 1000 and len(data) < limit) or (len(data) == 1000 and limit == 1000):
        return data
    if len(data) == 0:
        print(f'No results found for search term: {search_text}')
        return
    if len(data) > limit:
        return data.head(limit)

    spinner = spinning_cursor()
    for i in range(1, limit // max_results_per_request + 1):
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        offset = i* max_results_per_request
        next_data = _fetch_response(f'{url}&offset={offset}')
        next_data = pd.DataFrame(next_data['seriess'])
        if len(next_data) == 0:
            break
        data = pd.concat([data, next_data])
        sys.stdout.write('\b')
    if not discontinued:
        data = data[~data['title'].str.contains('DISCONTINUED')]
    # fetch more data if discontinued droped too many rows
    if len(data) < limit:
        next_data = _fetch_response(f'{url}&offset={len(data)}')
        next_data = pd.DataFrame(next_data['seriess'])
        data = pd.concat([data, next_data])
    if len(data) > limit:
        data = data.head(limit)
    return data


def get_series_in_category(category, discontinued = True, limit = 1000, order_by='series_id', sort_order='asc', filter=None):
    '''Get the series in a category.
    
    Parameters:
    category: str or int
        The category name or category_id to query.
    discontinued: bool
        If False exclude series which have "(DISCONTINUED)" string in title. Default is True.
    order_by: str
        Optional: order results by values of the specified attribute.
        One of the following strings: 'series_id', 'title', 'units', 'frequency', 'seasonal_adjustment', 'realtime_start', 'realtime_end', 'last_updated', 'observation_start', 'observation_end', 'popularity', 'group_popularity'.
        Default: series_id
    sort_order: str
        Optional: sort order of the results.
        One of the following strings: 'asc', 'desc'.
        Default: asc
    filter: tuple
        Optional: filter results by values of the specified attribute.
        Two item tuple: (filter_variable, filter_value)
        One of the following strings: 'frequency', 'units', 'seasonal_adjustment'.
        Default: None
        Example: ('seasonal_adjustment', 'Not Seasonally Adjusted')

    Returns:
    pd.DataFrame: df with metadata of all the series in category.
    
    '''
    max_results_per_request = 1000
    category_id = _get_category_id(category)
    if category_id is None:
        print(f'Category "{category}" not found.')
        return None
    url = f'{ROOT_URL}/category/series?category_id={category_id}'
    url = f'{url}&api_key={API_KEY}&file_type={FILE_TYPE}'
    url = _add_order_by(url, order_by)
    url = _add_sort_order(url, sort_order)
    url = _add_filter(url, filter)
    
    response = _fetch_response(url)
    if 'error_code' in response:
        print(response['error_message'])
        return
    data = pd.DataFrame(response['seriess'])

    if (len(data) < 1000 and len(data) < limit) or (len(data) == 1000 and limit == 1000):
        return data
    if len(data) == 0:
        print(f'No series found in category: {category}')
        return
    if len(data) > limit:
        return data.head(limit)
    
    spinner = spinning_cursor()
    for i in range(1, limit // max_results_per_request + 1):
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        offset = i * max_results_per_request
        next_data = _fetch_response(f'{url}&offset={offset}')
        next_data = pd.DataFrame(next_data['seriess'])
        if len(next_data) == 0:
            break
        data = pd.concat([data, next_data])
        sys.stdout.write('\b')
    if not discontinued:
        data = data[~data['title'].str.contains('DISCONTINUED')]
    if len(data) > limit:
        data = data.head(limit)
    return response


def _get_last_tree_node(tree):
    '''Get the last node in a tree.'''
    for pre, fill, node in RenderTree(tree):
        pass
    return node


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


print_tree(depth=0)
print_tree(depth=1) 
print_tree(depth=2)

print_tree(category = 'National Income & Product Accounts')
print_tree(category = 'Personal Loan Rates')
print_tree(category = 'Money Market Accounts')
print_tree(category = 'Weekly Initial Claims')
print_tree(category = 22)

print_tree(category = 33058, discontinued=True)
print_tree(category = 33058, discontinued=False)
print_tree(category = 'National Income & Product Accounts')

get_category_meta('Kosovo')
get_category_meta(32946)
get_series_in_category('Kosovo')
get_series_in_category(32946)
get_series_in_category('Kosovo', discontinued=False)

get_observations('TERMCBPER24NS')
get_series_meta('TERMCBPER24NS')
get_observations('ALKSVA05N') # should return error message
get_observations('OBMMIC30YFLVLE80FLT680')
get_categories() 
get_category_meta(117)
get_category_meta('Prime Bank Loan Rate')
get_subcategories('Interest Rates')
get_subcategories('AMERIBOR Benchmark Rates')
get_subcategories(22)
get_subcategories(34009) # should return no children
get_subcategories('AMERIBOR Benchmark Rates') # should return no children


'''
TODO: 
- OOP
- environment vars
- documentation
'''

results = search('stock', limit = 4246, discontinued = False)

