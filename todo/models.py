from django.db import models
from django.conf import settings
from django.utils import timezone


# Create your models here.
class Task(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    posted_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(null=True, blank=True)
    order = models.IntegerField(default=0, verbose_name='並び順')

    def is_overdue(self, dt):
        if self.due_at is None:
            return False
        return self.due_at < dt

    PRIORITY_CHOICES = (
        (1, '高'),
        (2, '中'),
        (3, '低'),
    )
    
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES, 
        default=2, 
        verbose_name='優先度'
    )

    class Meta:
        ordering = ['order', '-posted_at'] 