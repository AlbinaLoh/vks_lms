from django.contrib import admin

# Register your models here.
from .models import Student, Faculty, Course, Department, Assignment, Announcement, News, CourseRequest

admin.site.register(Student)
admin.site.register(Faculty)
admin.site.register(Course)
admin.site.register(Department)
admin.site.register(Assignment)
admin.site.register(Announcement)
admin.site.register(News)
admin.site.register(CourseRequest)
