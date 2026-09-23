from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from .models import UsuarioPersonalizado, Departamento
from django.contrib.auth.hashers import make_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioPersonalizado
        fields = ['id', 'username', 'password', 'email', 'rol', 'telefono']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Credenciales incorrectas")
    
class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'nombre']

class UsuarioSerializer(serializers.ModelSerializer):
    departamento = DepartamentoSerializer(read_only=True)
    departamento_id = serializers.PrimaryKeyRelatedField(
        queryset=Departamento.objects.all(), 
        source='departamento',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = UsuarioPersonalizado
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name', 
                 'rol', 'departamento', 'departamento_id', 'telefono', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_active': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class UsuarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioPersonalizado
        fields = ['email', 'first_name', 'last_name', 'rol', 'departamento', 'telefono', 'is_active']
