from utils  import distance
class Shop():
    def __init__(self, shop_id, shop_name, shop_address, shop_lat, shop_long, shop_radius):
        self.shop_id = shop_id
        self.shop_name = shop_name
        self.shop_address = shop_address
        self.shop_lat = shop_lat
        self.shop_long = shop_long
        self.shop_radius = shop_radius

    def __str__(self):
        return f"{self.shop_id} - {self.shop_name} - {self.shop_address} - {self.shop_lat} - {self.shop_long} - {self.shop_radius}"
    
    def calculate_distance(self, user_lat, user_long):
        return distance((self.shop_lat, self.shop_long), (user_lat, user_long)).miles