def get_user(user_id):
<<<<<<< HEAD
    if user_id in cache:
        return cache[user_id]
    return db.query(user_id)
=======
    def get_user(user_id: str) -> User:
        return db.query(user_id)
>>>>>>> feature/types
