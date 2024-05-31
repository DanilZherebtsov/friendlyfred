from lxml import etree
from tqdm import tqdm
from common import get_children, get_categories, http


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
                child['children'] = get_children(child_id)
        _save_categories(categories)
        return categories
    except Exception as e:
        print(f'Error updating categories: {e}')
        print('\nReturning initial categories.')
        return get_categories()
