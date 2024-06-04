**friendlyfred** package to query the `FRED <https://fred.stlouisfed.org>` database - Federal Reserve Economic Data. 

The package is a Python wrapper for the `FRED API <https://fred.stlouisfed.org/docs/api/fred/>`_.

The package allows for a simple interface to query the FRED database and retrieve data in a tabular format. 

The package also has a built-in functionality to display all the available FRED categories with it's handy print_tree() method.

Display major categories:

``fred.print_tree(depth = 0)``

.. image:: img/tree_depth_0.png


Show all categories and their subcategories:

``fred.print_tree(depth = 2)``

.. image:: img/tree_depth_2.png

Show available series for a category:

``fred.print_tree(category = 'Money Market Accounts')``

.. image:: img/tree_series.png

Get data for any series:

``fred.get_observations('MMNRJD')``

.. image:: img/observations.png