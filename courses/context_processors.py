from .models import Level

def menu_data(request):

    levels = Level.objects.all()

    return {
        'levels': levels
    }