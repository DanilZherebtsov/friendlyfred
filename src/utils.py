def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor
