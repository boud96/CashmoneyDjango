class BaseFilter:
    def __init__(self):
        self.filter_params = {}

    def set_param(self, key, value):
        """Sets a filter parameter key-value pair."""
        self.filter_params[key] = value

    def get_param(self, key):
        """Gets the value of a specific filter parameter."""
        return self.filter_params.get(key)

    def clear_params(self):
        """Clears all filter parameters."""
        self.filter_params.clear()