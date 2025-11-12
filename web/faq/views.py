from django.conf import settings
from django.shortcuts import render
from django.template.context_processors import csrf
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


# Create your views here.
from core.views import catch_error


@catch_error
def index(request):
    return render(request, "faq/faq.html")


@catch_error
def send_form(request):

    if request.POST:
        name = request.POST['name']
        email = request.POST['faq_email']
        message = request.POST['message']

        html_content = render_to_string('faq/faq_email.html', {
            'name': name,
            'email': email,
            'message': message,
        })
        subject = 'Сообщение с формы обратной связи'
        msg = EmailMultiAlternatives(subject, '', settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
        msg.attach_alternative(html_content, "text/html")

        if settings.IS_LOCAL_ENVIRONMENT:
            print(msg)
        else:
            msg.send(fail_silently=False)

        return render(request, "faq/faq.html")
