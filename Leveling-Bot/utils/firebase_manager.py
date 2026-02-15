import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import math
import os

class FirebaseManager:
    def __init__(self, cred_path='config/serviceAccountKey.json'):
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials not found at: {cred_path}")
        
        database_url = os.getenv('FIREBASE_DATABASE_URL')
        if not database_url:
            raise ValueError("FIREBASE_DATABASE_URL not found in .env file")
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {'databaseURL': database_url})
        self.db_ref = db.reference()
    
    def _get_current_week(self):
        now = datetime.now()
        week_number = now.isocalendar()[1]
        year = now.year
        return f"{year}-W{week_number:02d}"
    
    def _get_stored_week(self):
        week_ref = self.db_ref.child('week')
        stored_week = week_ref.get()
        return stored_week
    
    def _check_and_reset_weekly(self):
        current_week = self._get_current_week()
        stored_week = self._get_stored_week()
        
        if stored_week != current_week:
            week_ref = self.db_ref.child('week')
            week_ref.set(current_week)
            
            users_ref = self.db_ref.child('users')
            all_users = users_ref.get()
            
            if all_users:
                for user_id in all_users:
                    user_ref = self.db_ref.child('users').child(user_id)
                    user_ref.update({'messageCount': 0})
            
            return True
        return False
    
    def _create_default_user(self, user_id):
        return {
            'userId': str(user_id),
            'lastMessageTime': None,
            'level': 0,
            'messageCount': 0,
            'currentXP': 0,
            'totalXP': 0,
            'roles': {
                'Red': False,
                'Orange': False,
                'Teal': False,
                'Blue': False,
                'Purple': False,
                'Black': False,
                'Custom Role 1': False,
                'Custom Role 2': False,
                'Special Role 1': False,
                'Special Role 2': False,
            },
            'items': {
                'tiny_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'small_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'medium_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'large_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'custom_role_pass': {'amount': 0, 'timeActivated': None, 'roleId': None}
            }
        }   
    
    def calculate_xp_for_level(self, level):
        return math.floor(12.25 * (level ** 2))
    
    def calculate_level_from_xp(self, total_xp):
        if total_xp <= 0:
            return 0
        level = math.floor(math.sqrt(total_xp / 12.25))
        return level
    
    def get_xp_for_next_level(self, current_level):
        return self.calculate_xp_for_level(current_level + 1)
    
    def get_xp_in_current_level(self, total_xp, current_level):
        xp_at_level_start = self.calculate_xp_for_level(current_level)
        return total_xp - xp_at_level_start
    
    def get_user_data(self, user_id):
        user_ref = self.db_ref.child('users').child(str(user_id))
        user_data = user_ref.get()
        
        if not user_data:
            new_user = self._create_default_user(user_id)
            user_ref.set(new_user)
            return new_user
        
        return user_data
    
    def add_xp(self, user_id, username, xp_amount):
        self._check_and_reset_weekly()
        
        user_data = self.get_user_data(user_id)
        
        old_level = user_data['level']
        new_current_xp = user_data['currentXP'] + xp_amount
        
        if xp_amount > 0:
            new_total_xp = user_data['totalXP'] + xp_amount
        else:
            new_total_xp = user_data['totalXP']
        
        new_level = self.calculate_level_from_xp(new_total_xp)
        
        user_ref = self.db_ref.child('users').child(str(user_id))
        user_ref.update({
            'currentXP': new_current_xp,
            'totalXP': new_total_xp,
            'level': new_level,
            'messageCount': user_data['messageCount'],
            'lastUsername': username,
            'lastMessageTime': datetime.now().isoformat()
        })
        
        leveled_up = new_level > old_level
        
        return {
            'leveled_up': leveled_up,
            'old_level': old_level,
            'new_level': new_level,
            'xp_gain': xp_amount,
            'current_xp': new_current_xp,
            'total_xp': new_total_xp
        }
    
    def reset_user(self, user_id):
        user_ref = self.db_ref.child('users').child(str(user_id))
        user_ref.update({
            'userId': str(user_id),
            'lastMessageTime': None,
            'level': 0,
            'messageCount': 0,
            'currentXP': 0,
            'totalXP': 0,
            'roles': {
                'Red': False,
                'Orange': False,
                'Teal': False,
                'Blue': False,
                'Purple': False,
                'Black': False,
                'Custom Role 1': False,
                'Custom Role 2': False,
                'Special Role 1': False,
                'Special Role 2': False,
            },
            'items': {
                'tiny_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'small_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'medium_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'large_booster': {'amount': 0, 'active': 0, 'timeActivated': None},
                'custom_role_pass': {'amount': 0, 'timeActivated': None, 'roleId': None}
            }
        })
    
    def get_leaderboard(self, limit=10):
        users_ref = self.db_ref.child('users')
        all_users = users_ref.get()
        
        if not all_users:
            return []
        
        users_list = [user_data for user_id, user_data in all_users.items()]
        users_list.sort(key=lambda x: x.get('totalXP', 0), reverse=True)
        
        leaderboard = []
        for idx, user in enumerate(users_list[:limit]):
            user['rank'] = idx + 1
            leaderboard.append(user)
        
        return leaderboard
    
    def get_user_rank(self, user_id):
        user_data = self.get_user_data(user_id)
        user_xp = user_data['totalXP']
        
        users_ref = self.db_ref.child('users')
        all_users = users_ref.get()
        
        if not all_users:
            return 1
        
        higher_users = sum(1 for uid, data in all_users.items() if data.get('totalXP', 0) > user_xp)
        return higher_users + 1
    
    def get_weekly_leaderboard(self, limit=10):
        users_ref = self.db_ref.child('users')
        all_users = users_ref.get()
        
        if not all_users:
            return []
        
        weekly_data = []
        
        for user_id, user_data in all_users.items():
            weekly_data.append({
                'userId': user_id,
                'username': user_data.get('lastUsername', 'Unknown'),
                'messageCount': user_data.get('messageCount', 0)
            })
        
        weekly_data.sort(key=lambda x: x['messageCount'], reverse=True)
        
        return weekly_data[:limit]
    
    def set_user_role(self, user_id, role_name, value=True):
        user_ref = self.db_ref.child('users').child(str(user_id)).child('roles')
        user_ref.update({role_name: value})
    
    def get_user_roles(self, user_id):
        user_data = self.get_user_data(user_id)
        return user_data.get('roles', {})
    
    def add_item(self, user_id, item_name, amount=1):
        user_data = self.get_user_data(user_id)
        current_amount = user_data.get('items', {}).get(item_name, {}).get('amount', 0)
        
        user_ref = self.db_ref.child('users').child(str(user_id)).child('items').child(item_name)
        user_ref.update({'amount': current_amount + amount})
    
    def use_item(self, user_id, item_name):
        user_data = self.get_user_data(user_id)
        item_data = user_data.get('items', {}).get(item_name, {})
        
        if item_data.get('amount', 0) <= 0:
            return False
        
        user_ref = self.db_ref.child('users').child(str(user_id)).child('items').child(item_name)
        user_ref.update({
            'amount': item_data['amount'] - 1,
            'active': 1,
            'timeActivated': datetime.now().isoformat()
        })
        return True
    
    def deactivate_item(self, user_id, item_name):
        user_ref = self.db_ref.child('users').child(str(user_id)).child('items').child(item_name)
        user_ref.update({'active': 0, 'timeActivated': None})
    
    def get_user_items(self, user_id):
        user_data = self.get_user_data(user_id)
        return user_data.get('items', {})
    
    def get_active_boosters(self, user_id):
        items = self.get_user_items(user_id)
        active_boosters = []
        
        for item_name, item_data in items.items():
            if 'booster' in item_name and item_data.get('active', 0) == 1:
                active_boosters.append({
                    'name': item_name,
                    'timeActivated': item_data.get('timeActivated')
                })
        
        return active_boosters
    
    def get_all_active_boosters_all_users(self):
        all_users_ref = self.db_ref.child('users')
        all_users = all_users_ref.get()
        
        if not all_users:
            return {}
        
        active_boosters_map = {}
        
        for user_id, user_data in all_users.items():
            items = user_data.get('items', {})
            active = [
                item_name for item_name, item_data in items.items()
                if 'booster' in item_name and item_data.get('active', 0) == 1
            ]
            
            if active:
                active_boosters_map[user_id] = active
        
        return active_boosters_map
    
    def check_booster_expiry(self, user_id, booster_name, duration_minutes):
        items = self.get_user_items(user_id)
        booster = items.get(booster_name, {})
        
        if booster.get('active', 0) == 0:
            return False
        
        time_activated = booster.get('timeActivated')
        if not time_activated:
            return False
        
        try:
            activated_time = datetime.fromisoformat(time_activated)
            current_time = datetime.now()
            time_diff = (current_time - activated_time).total_seconds() / 60
            
            return time_diff >= duration_minutes
        except Exception as e:
            print(f"Error checking booster expiry: {e}")
            return False
    
    def set_custom_role_id(self, user_id, role_id):
        user_ref = self.db_ref.child('users').child(str(user_id)).child('items').child('custom_role_pass')
        user_ref.update({'roleId': role_id})
        print(f"Stored custom role ID {role_id} for user {user_id}")

    def get_all_users_with_custom_roles(self):
        users_ref = self.db_ref.child('users')
        all_users = users_ref.get() or {}
        
        users_with_crp = {}
        
        for user_id, user_data in all_users.items():
            items = user_data.get('items', {})
            crp_data = items.get('custom_role_pass', {})
            
            if crp_data.get('timeActivated') and crp_data.get('roleId'):
                users_with_crp[user_id] = crp_data
        
        return users_with_crp

    def clear_custom_role_pass(self, user_id):
        user_ref = self.db_ref.child('users').child(str(user_id)).child('items').child('custom_role_pass')
        user_ref.update({
            'timeActivated': None,
            'roleId': None
        })
        print(f"Cleared custom role pass data for user {user_id}")

firebase_manager = FirebaseManager()