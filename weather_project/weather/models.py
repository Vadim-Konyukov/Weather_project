from django.db import models

class SearchHistory(models.Model):
    session_key = models.CharField(max_length=40)
    city = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_key} searched for {self.city} on {self.timestamp}"
