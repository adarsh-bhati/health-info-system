from flask_login import UserMixin


class MongoUser(UserMixin):

    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data["_id"])
        self.username = user_data.get("username")
        self.email = user_data.get("email")
        self.phone = user_data.get("phone")
        self.is_admin = user_data.get("is_admin", False)

    def get_id(self):
        return self.id