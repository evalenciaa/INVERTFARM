from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Departamento

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(request=self.context.get('request'), **data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Credenciales incorrectas")
    
class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'nombre']
