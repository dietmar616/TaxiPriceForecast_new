from django.contrib import admin
from django.urls import path
from PriceWise import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('calculate_price/', views.calculate_price, name='calculate_price'),
    path('save_trip/', views.save_trip, name='save_trip'),
    path('add_driver/', views.addDriver, name='add_driver'),
    path('loadDrivers/', views.loadDrivers, name='loadDrivers'),
    path('create_df/', views.create_df, name='create_df'),
    path('predictions_page/', views.predictions_page, name='predictions_page'),
    path('get_predictions/', views.get_predictions, name='get_predictions'),
    path('', views.calculate_price, name='price_calculator'),
]
