from .models import Restaurant, Table, Booking, TimeSlot
from .serializers import RestaurantSerializer, TableSerializer, BookingSerializer, TimeSlotSerializer, RegisterSerializer
from rest_framework import viewsets, permissions, filters, generics, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from django.utils import timezone

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address']
    ordering_fields = ['name']
    ordering = ['name']


    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]  # Только админ может создавать, изменять, удалять
        return [permissions.AllowAny()]  # Пользователь может только смотреть

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.select_related('restaurant').all()
    serializer_class = TableSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['table_number', 'restaurant__name']
    filterset_fields = ['restaurant', 'capacity']
    ordering_fields = ['table_number', 'capacity']
    ordering = ['table_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]  # Только админ может создавать, изменять, удалять
        return [permissions.AllowAny()]  # Пользователь может только смотреть

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Получить столики с доступными слотами"""
        from datetime import timedelta

        restaurant_id = request.query_params.get('restaurant')
        capacity = request.query_params.get('capacity')
        date = request.query_params.get('date')

        queryset = self.get_queryset()

        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if capacity:
            queryset = queryset.filter(capacity__gte=capacity)

        # Фильтрация столиков с доступными слотами
        if date:
            target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
            start_datetime = timezone.make_aware(timezone.datetime.combine(target_date, timezone.datetime.min.time()))
            end_datetime = start_datetime + timedelta(days=1)

            tables_with_available_slots = Table.objects.filter(
                time_slots__status='free',
                time_slots__start_time__gte=start_datetime,
                time_slots__start_time__lt=end_datetime
            ).distinct()

            queryset = queryset.filter(id__in=tables_with_available_slots)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('user', 'table', 'table__restaurant', 'time_slot').all()
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['table', 'table__restaurant']
    ordering_fields = ['created_at', 'time_slot__start_time']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Так сможем разграничить направленность пользователя, если он часть команды сервиса is_staff==True, то он
        видит всё, если это обычный пользователь, то видит только свои брони
        :return:
        """
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)

    def get_permissions(self):
        if self.action in ['list', 'create', 'retrieve', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        user = self.serializer_class(data=request.data)
        user.is_valid(raise_exception=True)
        created_user = user.save()
        refresh = RefreshToken.for_user(created_user)
        return Response({
            "user": user.data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.select_related('table', 'table__restaurant').all()
    serializer_class = TimeSlotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'table', 'table__restaurant']
    ordering_fields = ['start_time', 'end_time']
    ordering = ['start_time']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Для обычных пользователей показываем только будущие слоты
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                start_time__gte=timezone.now()
            )

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]  # Только админ может создавать, изменять, удалять
        return [permissions.AllowAny()]  # Пользователь может только смотреть

    @action(detail=False, methods=['get'])
    def available(self, request):
        # Получить доступные слоты времени с фильтрацией
        queryset = self.get_queryset().filter(
            status='free',
            start_time__gte=timezone.now()
        )

        restaurant = request.query_params.get('restaurant')
        table_id = request.query_params.get('table')
        date = request.query_params.get('date')

        if restaurant:
            queryset = queryset.filter(table__restaurant_id=restaurant)
        if table_id:
            queryset = queryset.filter(table_id=table_id)
        if date:
            try:
                target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
                start_datetime = timezone.make_aware(
                    timezone.datetime.combine(target_date, timezone.datetime.min.time()))
                end_datetime = start_datetime + timezone.timedelta(days=1)
                queryset = queryset.filter(
                    start_time__gte=start_datetime,
                    start_time__lt=end_datetime
                )
            except ValueError:
                return Response(
                    {"detail": "Неверный формат даты. Нужно: YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)