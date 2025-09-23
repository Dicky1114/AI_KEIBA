"""
Accounts API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from .models import CustomUser, UserPreference
from .serializers import UserSerializer, UserPreferenceSerializer, UserRegistrationSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ユーザー API ViewSet
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 管理者以外は自分の情報のみ
        if self.request.user.is_staff:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        """現在のユーザー情報"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """
    ユーザー設定 API ViewSet
    """
    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)


class LoginAPIView(APIView):
    """
    ログイン API
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'success': True,
                    'token': token.key,
                    'user': UserSerializer(user).data
                })
        
        return Response({
            'success': False,
            'message': 'ユーザー名またはパスワードが正しくありません。'
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    """
    ログアウト API
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass
        
        logout(request)
        return Response({'success': True, 'message': 'ログアウトしました。'})


class RegisterAPIView(APIView):
    """
    ユーザー登録 API
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # ユーザー設定の初期作成
            UserPreference.objects.create(user=user)
            
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'success': True,
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
