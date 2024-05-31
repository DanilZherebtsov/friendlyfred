import urllib3

http = urllib3.PoolManager()


def get_categories():
    """Return the categories from saved dictionary."""
    from categories import categories
    return categories


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