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
        try:
            users = UserJsonStorageService.load_users()
            
            # Ensure all data is JSON serializable
            import json
            try:
                # Test if data can be serialized
                json.dumps(users)
                print("DEBUG: Data is JSON serializable")
            except (TypeError, ValueError) as json_err:
                print(f"ERROR: Data not JSON serializable: {json_err}")
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
            
            return Response(users, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = str(e)
            print(f"ERROR loading users: {error_msg}")
            print(f"ERROR traceback:\n{error_details}")
            return Response(
                {
                    'error': 'Internal server error',
                    'details': error_msg,
                    'type': type(e).__name__
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

