"""
Django REST Framework views for users.
"""
import os
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .services import UserJsonStorageService


class UserListView(APIView):
    """List all users and create new users."""
    authentication_classes = []  # Disable authentication to bypass CSRF
    
    def get(self, request):
        """Get all users."""
        # #region agent log
        import json as json_module
        import os
        try:
            # Ensure directory exists
            log_dir = 'c:\\app\\d2xmoney\\.cursor'
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A,B,C,D', 'location': 'views.py:18', 'message': 'UserListView.get() entry', 'data': {}}, ensure_ascii=False) + '\n')
        except Exception as log_err:
            print(f"DEBUG LOG ERROR: {log_err}")
            # Fallback log
            try:
                with open('c:\\app\\d2xmoney\\backend\\debug_fallback.log', 'a', encoding='utf-8') as f:
                    f.write(f"UserListView.get() called - {log_err}\n")
            except:
                pass
        print("DEBUG: UserListView.get() called")
        # #endregion
        try:
            # #region agent log
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A', 'location': 'views.py:21', 'message': 'Before load_users() call', 'data': {}}, ensure_ascii=False) + '\n')
            # #endregion
            users = UserJsonStorageService.load_users()
            # #region agent log
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A,B,C', 'location': 'views.py:24', 'message': 'After load_users() call', 'data': {'users_count': len(users) if users else 0, 'users_type': str(type(users))}}, ensure_ascii=False) + '\n')
            # #endregion
            
            # Ensure all data is JSON serializable
            import json
            # #region agent log
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B', 'location': 'views.py:28', 'message': 'Before json.dumps() test', 'data': {'users_sample': str(users[:1]) if users and len(users) > 0 else 'empty'}}, ensure_ascii=False) + '\n')
            # #endregion
            try:
                # Test if data can be serialized
                json.dumps(users)
                print("DEBUG: Data is JSON serializable")
                # #region agent log
                with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B', 'location': 'views.py:32', 'message': 'json.dumps() succeeded', 'data': {}}, ensure_ascii=False) + '\n')
                # #endregion
            except (TypeError, ValueError) as json_err:
                print(f"ERROR: Data not JSON serializable: {json_err}")
                # #region agent log
                with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B', 'location': 'views.py:35', 'message': 'json.dumps() failed', 'data': {'error': str(json_err), 'error_type': type(json_err).__name__}}, ensure_ascii=False) + '\n')
                # #endregion
                # Convert any non-serializable objects
                def make_serializable(obj):
                    if isinstance(obj, dict):
                        return {k: make_serializable(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [make_serializable(item) for item in obj]
                    elif hasattr(obj, 'isoformat'):  # datetime objects
                        return obj.isoformat()
                    else:
                        return str(obj)
                users = make_serializable(users)
            
            # #region agent log
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A,B,C,D', 'location': 'views.py:45', 'message': 'Before Response() return', 'data': {'users_count': len(users) if users else 0}}, ensure_ascii=False) + '\n')
            # #endregion
            return Response(users, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = str(e)
            print(f"ERROR loading users: {error_msg}")
            print(f"ERROR traceback:\n{error_details}")
            # #region agent log
            try:
                log_data = {'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A,B,C,D', 'location': 'views.py:50', 'message': 'Exception caught in get()', 'data': {'error': error_msg, 'error_type': type(e).__name__, 'traceback': error_details[:1000]}}
                with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps(log_data, ensure_ascii=False) + '\n')
            except Exception as log_err:
                print(f"DEBUG LOG ERROR: {log_err}")
                # Fallback: write to a simpler location
                try:
                    with open('c:\\app\\d2xmoney\\backend\\error.log', 'a', encoding='utf-8') as f:
                        f.write(f"ERROR: {error_msg}\nTRACEBACK: {error_details}\n\n")
                except:
                    pass
            # #endregion
            # Print full error to console for immediate visibility
            print("=" * 80)
            print("ERROR IN UserListView.get():")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {error_msg}")
            print(f"Full Traceback:\n{error_details}")
            print("=" * 80)
            
            return Response(
                {
                    'error': 'Internal server error',
                    'details': error_msg,
                    'type': type(e).__name__,
                    'traceback': error_details.split('\n')[-10:] if error_details else []  # Last 10 lines of traceback
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create user."""
        try:
            from .serializers import UserSerializer
            serializer = UserSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation error', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate user ID
            user_id = UserJsonStorageService.generate_user_id()
            
            # Handle picture upload
            picture_path = None
            if 'picture' in request.FILES:
                picture_file = request.FILES['picture']
                file_extension = os.path.splitext(picture_file.name)[1]
                picture_filename = f"{user_id}_{picture_file.name}"
                picture_path = default_storage.save(
                    f"users/{picture_filename}",
                    ContentFile(picture_file.read())
                )
            
            # Create user object
            user_data = {
                'id': user_id,
                'name': serializer.validated_data['name'],
                'cpf': serializer.validated_data['cpf'],
                'account_provider': serializer.validated_data['account_provider'],
                'account_number': serializer.validated_data['account_number'],
                'picture': f"/media/{picture_path}" if picture_path else None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            
            # Save to JSON file
            users = UserJsonStorageService.load_users()
            users.append(user_data)
            UserJsonStorageService.save_users(users)
            
            # Create default allocation strategy for new user
            try:
                from users.models import User as UserModel
                from allocation_strategies.services import AllocationStrategyService
                user_obj = UserModel.objects.get(id=user_id)
                AllocationStrategyService.create_default_strategy(user_obj)
            except Exception as e:
                # Log error but don't fail user creation if strategy creation fails
                import traceback
                print(f"Warning: Failed to create default allocation strategy for user {user_id}: {e}")
                print(traceback.format_exc())
            
            return Response(user_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating user: {e}")
            print(error_details)
            return Response(
                {'error': 'Internal server error', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(APIView):
    """Get, update, or delete a user."""
    authentication_classes = []  # Disable authentication to bypass CSRF
    
    def get(self, request, user_id):
        """Get user by ID."""
        user = UserJsonStorageService.get_user_by_id(user_id)
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(user, status=status.HTTP_200_OK)
    
    def put(self, request, user_id):
        """Update user."""
        user = UserJsonStorageService.get_user_by_id(user_id)
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create serializer with existing data and context to exclude current user from uniqueness checks
        from .serializers import UserSerializer
        serializer = UserSerializer(
            data=request.data, 
            partial=True,
            context={'exclude_user_id': user_id}
        )
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation error', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update fields
        for field in ['name', 'cpf', 'account_provider', 'account_number']:
            if field in serializer.validated_data:
                user[field] = serializer.validated_data[field]
        
        # Handle picture update
        if 'picture' in request.FILES:
            # Delete old picture if exists
            if user.get('picture'):
                old_path = user['picture'].replace('/media/', '')
                if default_storage.exists(old_path):
                    default_storage.delete(old_path)
            
            # Save new picture
            picture_file = request.FILES['picture']
            file_extension = os.path.splitext(picture_file.name)[1]
            picture_filename = f"{user_id}_{picture_file.name}"
            picture_path = default_storage.save(
                f"users/{picture_filename}",
                ContentFile(picture_file.read())
            )
            user['picture'] = f"/media/{picture_path}"
        
        user['updated_at'] = datetime.now().isoformat()
        
        # Save to JSON file
        users = UserJsonStorageService.load_users()
        users = [u if u.get('id') != user_id else user for u in users]
        UserJsonStorageService.save_users(users)
        
        return Response(user, status=status.HTTP_200_OK)
    
    def delete(self, request, user_id):
        """Delete user."""
        from .models import User
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete picture file if exists
        if user.picture:
            picture_path = user.picture.replace('/media/', '')
            if default_storage.exists(picture_path):
                default_storage.delete(picture_path)
        
        # Delete from database
        user.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

