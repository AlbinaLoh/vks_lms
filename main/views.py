import datetime
import openpyxl
from openpyxl import Workbook
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from .models import Student, Course, Announcement, Assignment, Submission, Material, Faculty, Department, News, CourseRequest
from django.template.defaulttags import register
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect
from .forms import AnnouncementForm, AssignmentForm, MaterialForm, NewsForm
from django import forms
from django.core import validators
from datetime import date as dt_date
from django.utils import timezone

from quiz.models import Quiz, StudentAnswer
from attendance.models import Attendance
from collections import defaultdict

from django import forms


class LoginForm(forms.Form):
    id = forms.CharField(label='ID', max_length=10, validators=[
                         validators.RegexValidator(r'^\d+$', 'Please enter a valid number.')])
    password = forms.CharField(widget=forms.PasswordInput)


def is_student_authorised(request, code):
    course = Course.objects.get(code=code)
    if request.session.get('student_id') and course in Student.objects.get(student_id=request.session['student_id']).course.all():
        return True
    else:
        return False


def is_faculty_authorised(request, code):
    if request.session.get('faculty_id') and code in Course.objects.filter(faculty_id=request.session['faculty_id']).values_list('code', flat=True):
        return True
    else:
        return False


# Custom Login page for both student and faculty
def std_login(request):
    error_messages = []

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            id = form.cleaned_data['id']
            password = form.cleaned_data['password']

            if Student.objects.filter(student_id=id, password=password).exists():
                request.session['student_id'] = id
                return redirect('myCourses')
            elif Faculty.objects.filter(faculty_id=id, password=password).exists():
                request.session['faculty_id'] = id
                return redirect('facultyCourses')
            else:
                error_messages.append('Не верный ID')
        else:
            error_messages.append('IНе верная форма ввода данных.')
    else:
        form = LoginForm()

    if 'student_id' in request.session:
        return redirect('/my/')
    elif 'faculty_id' in request.session:
        return redirect('/facultyCourses/')

    context = {'form': form, 'error_messages': error_messages}
    return render(request, 'login_page.html', context)

# Clears the session on logout


def std_logout(request):
    request.session.flush()
    return redirect('std_login')


# Display all courses (student view)
def myCourses(request):
    try:
        if request.session.get('student_id'):
            student = Student.objects.get(
                student_id=request.session['student_id'])
            courses = student.course.all()
            faculty = student.course.all().values_list('faculty_id', flat=True)

            context = {
                'courses': courses,
                'student': student,
                'faculty': faculty
            }

            return render(request, 'main/myCourses.html', context)
        else:
            return redirect('std_login')
    except:
        return render(request, 'error.html')


# Display all courses (faculty view)
def facultyCourses(request):
    try:
        if request.session['faculty_id']:
            faculty = Faculty.objects.get(
                faculty_id=request.session['faculty_id'])
            courses = Course.objects.filter(
                faculty_id=request.session['faculty_id'])
            # Student count of each course to show on the faculty page
            studentCount = Course.objects.all().annotate(student_count=Count('students'))

            studentCountDict = {}

            for course in studentCount:
                studentCountDict[course.code] = course.student_count

            @register.filter
            def get_item(dictionary, course_code):
                return dictionary.get(course_code)

            context = {
                'courses': courses,
                'faculty': faculty,
                'studentCount': studentCountDict
            }

            return render(request, 'main/facultyCourses.html', context)

        else:
            return redirect('std_login')
    except:

        return redirect('std_login')


# Particular course page (student view)
def course_page(request, code):
    try:
        course = Course.objects.get(code=code)
        if is_student_authorised(request, code):
            try:
                announcements = Announcement.objects.filter(course_code=course)
                assignments = Assignment.objects.filter(
                    course_code=course.code)
                materials = Material.objects.filter(course_code=course.code)

            except:
                announcements = None
                assignments = None
                materials = None

            context = {
                'course': course,
                'announcements': announcements,
                'assignments': assignments[:3],
                'materials': materials,
                'student': Student.objects.get(student_id=request.session['student_id'])
            }

            return render(request, 'main/course.html', context)

        else:
            return redirect('std_login')
    except:
        return render(request, 'error.html')


# Particular course page (faculty view)
def course_page_faculty(request, code):
    course = Course.objects.get(code=code)
    if request.session.get('faculty_id'):
        try:
            announcements = Announcement.objects.filter(course_code=course)
            assignments = Assignment.objects.filter(
                course_code=course.code)
            materials = Material.objects.filter(course_code=course.code)
            studentCount = Student.objects.filter(course=course).count()

        except:
            announcements = None
            assignments = None
            materials = None

        context = {
            'course': course,
            'announcements': announcements,
            'assignments': assignments[:3],
            'materials': materials,
            'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']),
            'studentCount': studentCount
        }

        return render(request, 'main/faculty_course.html', context)
    else:
        return redirect('std_login')


def error(request):
    return render(request, 'error.html')


# Display user profile(student & faculty)
def profile(request, id):
    try:
        if request.session['student_id'] == id:
            student = Student.objects.get(student_id=id)
            return render(request, 'main/profile.html', {'student': student})
        else:
            return redirect('std_login')
    except:
        try:
            if request.session['faculty_id'] == id:
                faculty = Faculty.objects.get(faculty_id=id)
                return render(request, 'main/faculty_profile.html', {'faculty': faculty})
            else:
                return redirect('std_login')
        except:
            return render(request, 'error.html')


def addAnnouncement(request, code):
    if is_faculty_authorised(request, code):
        if request.method == 'POST':
            form = AnnouncementForm(request.POST)
            form.instance.course_code = Course.objects.get(code=code)
            if form.is_valid():
                form.save()
                messages.success(
                    request, 'Анонс успешно добавлен')
                return redirect('/faculty/' + str(code))
        else:
            form = AnnouncementForm()
        return render(request, 'main/announcement.html', {'course': Course.objects.get(code=code), 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']), 'form': form})
    else:
        return redirect('std_login')


def deleteAnnouncement(request, code, id):
    if is_faculty_authorised(request, code):
        try:
            announcement = Announcement.objects.get(course_code=code, id=id)
            announcement.delete()
            messages.warning(request, 'Анонс успешно удален')
            return redirect('/faculty/' + str(code))
        except:
            return redirect('/faculty/' + str(code))
    else:
        return redirect('std_login')


def editAnnouncement(request, code, id):
    if is_faculty_authorised(request, code):
        announcement = Announcement.objects.get(course_code_id=code, id=id)
        form = AnnouncementForm(instance=announcement)
        context = {
            'announcement': announcement,
            'course': Course.objects.get(code=code),
            'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']),
            'form': form
        }
        return render(request, 'main/update-announcement.html', context)
    else:
        return redirect('std_login')


def updateAnnouncement(request, code, id):
    if is_faculty_authorised(request, code):
        try:
            announcement = Announcement.objects.get(course_code_id=code, id=id)
            form = AnnouncementForm(request.POST, instance=announcement)
            if form.is_valid():
                form.save()
                messages.info(request, 'Анонс успешно изменен')
                return redirect('/faculty/' + str(code))
        except:
            return redirect('/faculty/' + str(code))

    else:
        return redirect('std_login')


def addAssignment(request, code):
    if is_faculty_authorised(request, code):
        if request.method == 'POST':
            form = AssignmentForm(request.POST, request.FILES)
            form.instance.course_code = Course.objects.get(code=code)
            if form.is_valid():
                form.save()
                messages.success(request, 'Лекционный материал успешно создан')
                return redirect('/faculty/' + str(code))
        else:
            form = AssignmentForm()
        return render(request, 'main/assignment.html', {'course': Course.objects.get(code=code), 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']), 'form': form})
    else:
        return redirect('std_login')


# def assignmentPage(request, code, id):
#     course = Course.objects.get(code=code)
#     if is_student_authorised(request, code):
#         assignment = Assignment.objects.get(course_code=course.code, id=id)
#         try:

#             submission = Submission.objects.get(assignment=assignment, student=Student.objects.get(
#                 student_id=request.session['student_id']))

#             context = {
#                 'assignment': assignment,
#                 'course': course,
#                 'submission': submission,
#                 'time': datetime.datetime.now(),
#                 'student': Student.objects.get(student_id=request.session['student_id']),
#                 'courses': Student.objects.get(student_id=request.session['student_id']).course.all()
#             }

#             return render(request, 'main/assignment-portal.html', context)

#         except:
#             submission = None

#         context = {
#             'assignment': assignment,
#             'course': course,
#             'submission': submission,
#             'time': datetime.datetime.now(),
#             'student': Student.objects.get(student_id=request.session['student_id']),
#             'courses': Student.objects.get(student_id=request.session['student_id']).course.all()
#         }

#         return render(request, 'main/assignment-portal.html', context)
#     else:

#         return redirect('std_login')

def assignmentPage(request, code, id):
    course = get_object_or_404(Course, code=code)
    if not is_student_authorised(request, code):
        return redirect('std_login')

    assignment = get_object_or_404(Assignment, course_code=course.code, id=id)
    student = get_object_or_404(Student, student_id=request.session['student_id'])

    try:
        submission = Submission.objects.get(assignment=assignment, student=student)
    except Submission.DoesNotExist:
        submission = None

    is_before_deadline = assignment.deadline > timezone.now()

    context = {
        'assignment': assignment,
        'course': course,
        'submission': submission,
        'time': timezone.now(),
        'student': student,
        'courses': student.course.all(),
        'is_before_deadline': is_before_deadline,
    }
    return render(request, 'main/assignment-portal.html', context)




def allAssignments(request, code):
    if is_faculty_authorised(request, code):
        course = Course.objects.get(code=code)
        assignments = Assignment.objects.filter(course_code=course)
        studentCount = Student.objects.filter(course=course).count()

        context = {
            'assignments': assignments,
            'course': course,
            'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']),
            'studentCount': studentCount

        }
        return render(request, 'main/all-assignments.html', context)
    else:
        return redirect('std_login')

def assignment_detail(request, course_code, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    course = get_object_or_404(Course, code=course_code)
    student = get_object_or_404(Student, student_id=request.session.get('student_id'))
    # Получение submission для этого assignment и студента
    submission = Submission.objects.filter(assignment=assignment, student=student).first()
    
    # ВАЖНО: вычисляем, открыт ли дедлайн (True, если дедлайн ещё не истёк)
    is_before_deadline = assignment.deadline > timezone.now()
    
    context = {
        'assignment': assignment,
        'course': course,
        'student': student,
        'submission': submission,
        'is_before_deadline': is_before_deadline,
        # ... другие переменные, если есть
    }
    return render(request, 'main/assignment_detail.html', context)

def allAssignmentsSTD(request, code):
    if is_student_authorised(request, code):
        course = Course.objects.get(code=code)
        assignments = Assignment.objects.filter(course_code=course)
        context = {
            'assignments': assignments,
            'course': course,
            'student': Student.objects.get(student_id=request.session['student_id']),

        }
        return render(request, 'main/all-assignments-std.html', context)
    else:
        return redirect('std_login')


# def addSubmission(request, code, id):
#     try:
#         course = Course.objects.get(code=code)
#         if is_student_authorised(request, code):
#             # check if assignment is open
#             assignment = Assignment.objects.get(course_code=course.code, id=id)
#             if assignment.deadline < datetime.datetime.now():

#                 return redirect('/assignment/' + str(code) + '/' + str(id))

#             if request.method == 'POST' and request.FILES['file']:
#                 assignment = Assignment.objects.get(
#                     course_code=course.code, id=id)
#                 submission = Submission(assignment=assignment, student=Student.objects.get(
#                     student_id=request.session['student_id']), file=request.FILES['file'],)
#                 submission.status = 'Submitted'
#                 submission.save()
#                 return HttpResponseRedirect(request.path_info)
#             else:
#                 assignment = Assignment.objects.get(
#                     course_code=course.code, id=id)
#                 submission = Submission.objects.get(assignment=assignment, student=Student.objects.get(
#                     student_id=request.session['student_id']))
#                 context = {
#                     'assignment': assignment,
#                     'course': course,
#                     'submission': submission,
#                     'time': datetime.datetime.now(),
#                     'student': Student.objects.get(student_id=request.session['student_id']),
#                     'courses': Student.objects.get(student_id=request.session['student_id']).course.all()
#                 }

#                 return render(request, 'main/assignment-portal.html', context)
#         else:
#             return redirect('std_login')
#     except:
#         return HttpResponseRedirect(request.path_info)

def addSubmission(request, code, id):
    course = get_object_or_404(Course, code=code)
    if not is_student_authorised(request, code):
        return redirect('std_login')

    assignment = get_object_or_404(Assignment, course_code=course.code, id=id)
    student = get_object_or_404(Student, student_id=request.session['student_id'])

    # Проверка дедлайна
    if assignment.deadline < timezone.now():
        messages.error(request, 'Дедлайн уже прошёл!')
        return redirect('assignmentPage', code=code, id=id)

    if request.method == 'POST' and request.FILES.get('file'):
        submission, created = Submission.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'status': 'Submitted'}
        )
        submission.file = request.FILES['file']
        submission.status = 'Submitted'
        submission.save()
        messages.success(request, 'Задание успешно отправлено!')
        return redirect('assignmentPage', code=code, id=id)

    # Если GET или нет файла, показываем страницу с текущей submission
    submission = Submission.objects.filter(assignment=assignment, student=student).first()
    context = {
        'assignment': assignment,
        'course': course,
        'submission': submission,
        'time': timezone.now(),
        'student': student,
        'courses': student.course.all()
    }
    return render(request, 'main/assignment-portal.html', context)












def viewSubmission(request, code, id):
    course = Course.objects.get(code=code)
    if is_faculty_authorised(request, code):
        try:
            assignment = Assignment.objects.get(course_code_id=code, id=id)
            submissions = Submission.objects.filter(
                assignment_id=assignment.id)

            context = {
                'course': course,
                'submissions': submissions,
                'assignment': assignment,
                'totalStudents': len(Student.objects.filter(course=course)),
                'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']),
                'courses': Course.objects.filter(faculty_id=request.session['faculty_id'])
            }

            return render(request, 'main/assignment-view.html', context)

        except:
            return redirect('/faculty/' + str(code))
    else:
        return redirect('std_login')


def gradeSubmission(request, code, id, sub_id):
    try:
        course = Course.objects.get(code=code)
        if is_faculty_authorised(request, code):
            if request.method == 'POST':
                assignment = Assignment.objects.get(course_code_id=code, id=id)
                submissions = Submission.objects.filter(
                    assignment_id=assignment.id)
                submission = Submission.objects.get(
                    assignment_id=id, id=sub_id)
                submission.marks = request.POST['marks']
                if request.POST['marks'] == 0:
                    submission.marks = 0
                submission.save()
                return HttpResponseRedirect(request.path_info)
            else:
                assignment = Assignment.objects.get(course_code_id=code, id=id)
                submissions = Submission.objects.filter(
                    assignment_id=assignment.id)
                submission = Submission.objects.get(
                    assignment_id=id, id=sub_id)

                context = {
                    'course': course,
                    'submissions': submissions,
                    'assignment': assignment,
                    'totalStudents': len(Student.objects.filter(course=course)),
                    'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']),
                    'courses': Course.objects.filter(faculty_id=request.session['faculty_id'])
                }

                return render(request, 'main/assignment-view.html', context)

        else:
            return redirect('std_login')
    except:
        return redirect('/error/')


def addCourseMaterial(request, code):
    if is_faculty_authorised(request, code):
        if request.method == 'POST':
            form = MaterialForm(request.POST, request.FILES)
            form.instance.course_code = Course.objects.get(code=code)
            if form.is_valid():
                form.save()
                messages.success(request, 'Новые материалы добавлены')
                return redirect('/faculty/' + str(code))
            else:
                return render(request, 'main/course-material.html', {'course': Course.objects.get(code=code), 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']), 'form': form})
        else:
            form = MaterialForm()
            return render(request, 'main/course-material.html', {'course': Course.objects.get(code=code), 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id']), 'form': form})
    else:
        return redirect('std_login')


def deleteCourseMaterial(request, code, id):
    if is_faculty_authorised(request, code):
        course = Course.objects.get(code=code)
        course_material = Material.objects.get(course_code=course, id=id)
        course_material.delete()
        messages.warning(request, 'Материалы удалены')
        return redirect('/faculty/' + str(code))
    else:
        return redirect('std_login')


def courses(request):
    if request.session.get('student_id') or request.session.get('faculty_id'):

        courses = Course.objects.all()
        if request.session.get('student_id'):
            student = Student.objects.get(
                student_id=request.session['student_id'])
        else:
            student = None
        if request.session.get('faculty_id'):
            faculty = Faculty.objects.get(
                faculty_id=request.session['faculty_id'])
        else:
            faculty = None

        enrolled = student.course.all() if student else None
        accessed = Course.objects.filter(
            faculty_id=faculty.faculty_id) if faculty else None

        context = {
            'faculty': faculty,
            'courses': courses,
            'student': student,
            'enrolled': enrolled,
            'accessed': accessed
        }

        return render(request, 'main/all-courses.html', context)

    else:
        return redirect('std_login')


def departments(request):
    if request.session.get('student_id') or request.session.get('faculty_id'):
        departments = Department.objects.all()
        if request.session.get('student_id'):
            student = Student.objects.get(
                student_id=request.session['student_id'])
        else:
            student = None
        if request.session.get('faculty_id'):
            faculty = Faculty.objects.get(
                faculty_id=request.session['faculty_id'])
        else:
            faculty = None
        context = {
            'faculty': faculty,
            'student': student,
            'deps': departments
        }

        return render(request, 'main/departments.html', context)

    else:
        return redirect('std_login')


def access(request, code):
    if request.session.get('student_id'):
        course = get_object_or_404(Course, code=code)
        student = get_object_or_404(Student, student_id=request.session['student_id'])
        
        if request.method == 'POST':
            if request.POST.get('key') == str(course.studentKey):
                student.course.add(course)
                student.save()
                
                # Обновляем статус заявки в CourseRequest на 'approved'
                CourseRequest.objects.filter(
                    student=student,
                    course=course,
                    status='pending'  # обновляем только заявки в ожидании
                ).update(status='approved')
                
                return redirect('/my/')
            else:
                messages.error(request, 'Не верный ключ')
                return HttpResponseRedirect(request.path_info)
        else:
            return render(request, 'main/access.html', {'course': course, 'student': student})
    else:
        return redirect('std_login')






def search(request):
    if request.session.get('student_id') or request.session.get('faculty_id'):
        if request.method == 'GET' and request.GET['q']:
            q = request.GET['q']
            courses = Course.objects.filter(Q(code__icontains=q) | Q(
                name__icontains=q) | Q(faculty__name__icontains=q))

            if request.session.get('student_id'):
                student = Student.objects.get(
                    student_id=request.session['student_id'])
            else:
                student = None
            if request.session.get('faculty_id'):
                faculty = Faculty.objects.get(
                    faculty_id=request.session['faculty_id'])
            else:
                faculty = None
            enrolled = student.course.all() if student else None
            accessed = Course.objects.filter(
                faculty_id=faculty.faculty_id) if faculty else None

            context = {
                'courses': courses,
                'faculty': faculty,
                'student': student,
                'enrolled': enrolled,
                'accessed': accessed,
                'q': q
            }
            return render(request, 'main/search.html', context)
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        return redirect('std_login')


def changePasswordPrompt(request):
    if request.session.get('student_id'):
        student = Student.objects.get(student_id=request.session['student_id'])
        return render(request, 'main/changePassword.html', {'student': student})
    elif request.session.get('faculty_id'):
        faculty = Faculty.objects.get(faculty_id=request.session['faculty_id'])
        return render(request, 'main/changePasswordFaculty.html', {'faculty': faculty})
    else:
        return redirect('std_login')


def changePhotoPrompt(request):
    if request.session.get('student_id'):
        student = Student.objects.get(student_id=request.session['student_id'])
        return render(request, 'main/changePhoto.html', {'student': student})
    elif request.session.get('faculty_id'):
        faculty = Faculty.objects.get(faculty_id=request.session['faculty_id'])
        return render(request, 'main/changePhotoFaculty.html', {'faculty': faculty})
    else:
        return redirect('std_login')


def changePassword(request):
    if request.session.get('student_id'):
        student = Student.objects.get(
            student_id=request.session['student_id'])
        if request.method == 'POST':
            if student.password == request.POST['oldPassword']:
                # New and confirm password check is done in the client side
                student.password = request.POST['newPassword']
                student.save()
                messages.success(request, 'Пароль успешно изменен')
                return redirect('/profile/' + str(student.student_id))
            else:
                messages.error(
                    request, 'Не верный пароль')
                return redirect('/changePassword/')
        else:
            return render(request, 'main/changePassword.html', {'student': student})
    else:
        return redirect('std_login')


def changePasswordFaculty(request):
    if request.session.get('faculty_id'):
        faculty = Faculty.objects.get(
            faculty_id=request.session['faculty_id'])
        if request.method == 'POST':
            if faculty.password == request.POST['oldPassword']:
                # New and confirm password check is done in the client side
                faculty.password = request.POST['newPassword']
                faculty.save()
                messages.success(request, 'Пароль успешно изменен')
                return redirect('/facultyProfile/' + str(faculty.faculty_id))
            else:
                print('error')
                messages.error(
                    request, 'Не верный пароль')
                return redirect('/changePasswordFaculty/')
        else:
            print(faculty)
            return render(request, 'main/changePasswordFaculty.html', {'faculty': faculty})
    else:
        return redirect('std_login')


def changePhoto(request):
    if request.session.get('student_id'):
        student = Student.objects.get(
            student_id=request.session['student_id'])
        if request.method == 'POST':
            if request.FILES['photo']:
                student.photo = request.FILES['photo']
                student.save()
                messages.success(request, 'Фото успешно изменено')
                return redirect('/profile/' + str(student.student_id))
            else:
                messages.error(
                    request, 'Загрузите фото')
                return redirect('/changePhoto/')
        else:
            return render(request, 'main/changePhoto.html', {'student': student})
    else:
        return redirect('std_login')


def changePhotoFaculty(request):
    if request.session.get('faculty_id'):
        faculty = Faculty.objects.get(
            faculty_id=request.session['faculty_id'])
        if request.method == 'POST':
            if request.FILES['photo']:
                faculty.photo = request.FILES['photo']
                faculty.save()
                messages.success(request, 'Фото успешно изменено')
                return redirect('/facultyProfile/' + str(faculty.faculty_id))
            else:
                messages.error(
                    request, 'Загрузите фото')
                return redirect('/changePhotoFaculty/')
        else:
            return render(request, 'main/changePhotoFaculty.html', {'faculty': faculty})
    else:
        return redirect('std_login')


def guestStudent(request):
    request.session.flush()
    try:
        student = Student.objects.get(name='Guest Student')
        request.session['student_id'] = str(student.student_id)
        return redirect('myCourses')
    except:
        return redirect('std_login')


def guestFaculty(request):
    request.session.flush()
    try:
        faculty = Faculty.objects.get(name='Guest Faculty')
        request.session['faculty_id'] = str(faculty.faculty_id)
        return redirect('facultyCourses')
    except:
        return redirect('std_login')

def news_list(request):
    student_id = request.session.get('student_id')
    student = None
    faculty = None
    if student_id:
        student = Student.objects.filter(student_id=student_id).first()
    else:
        faculty_id = request.session.get('faculty_id')
        if faculty_id:
            faculty = Faculty.objects.filter(faculty_id=faculty_id).first()
    news = News.objects.all()
    return render(request, 'main/news_list.html', {
        'student': student,
        'faculty': faculty,
        'news': news,
    })
   
    return render(request, 'main/news_list.html', {'student': student, 'news': news})
def news_detail(request, pk):
    try:
        news = get_object_or_404(News, pk=pk)
        context = {
            'news': news
        }
        
        # Если пользователь - преподаватель, добавляем это в контекст
        if request.session.get('faculty_id'):
            faculty = Faculty.objects.get(faculty_id=request.session['faculty_id'])
            context['faculty'] = faculty
            
        return render(request, 'main/news_detail.html', context)
    except Exception:
        return render(request, 'error.html')


def news_create(request):
    try:
        if request.session.get('faculty_id'):
            faculty = Faculty.objects.get(faculty_id=request.session['faculty_id'])
        else:
            return redirect('std_login')  # или redirect('news_list')

        if request.method == 'POST':
            form = NewsForm(request.POST)
            if form.is_valid():
                news = form.save(commit=False)
                news.faculty = faculty
                news.save()
                messages.success(request, "Новость успешно создана.")
                return redirect('news_list')
        else:
            form = NewsForm()

        return render(request, 'main/news_form.html', {'form': form, 'title': 'Создать новость'})

    except Faculty.DoesNotExist:
        messages.error(request, "Преподаватель не найден.")
        return redirect('std_login')
    except Exception:
        return render(request, 'error.html')

def news_edit(request, pk):
    try:
        if request.session.get('faculty_id'):
            faculty = Faculty.objects.get(faculty_id=request.session['faculty_id'])
        else:
            return redirect('std_login')  # или redirect('news_list')

        news = get_object_or_404(News, pk=pk)

        if news.faculty != faculty:
            messages.error(request, "Вы можете редактировать только свои новости.")
            return redirect('news_list')

        if request.method == 'POST':
            form = NewsForm(request.POST, instance=news)
            if form.is_valid():
                form.save()
                messages.success(request, "Новость успешно обновлена.")
                return redirect('news_list')
        else:
            form = NewsForm(instance=news)

        return render(request, 'main/news_form.html', {'form': form, 'title': 'Редактировать новость'})

    except Faculty.DoesNotExist:
        messages.error(request, "Преподаватель не найден.")
        return redirect('std_login')
    except Exception:
        return render(request, 'error.html')
    





def export_students_statistics(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('std_login')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Статистика студентов"

    # Заголовки с дополнительными столбцами
    ws.append([
        "Направление",
        "Курс",
        "Код курса",
        "ФИО студента",
        "E-mail студента",
        "Дата первой лекции (первого задания)",
        "Оценка за тест",
        "Дата сдачи теста",
        "Посещено/Всего"
    ])
    courses = Course.objects.filter(faculty_id=faculty_id)
    for course in courses:
        students = course.students.all()

        first_assignment = Assignment.objects.filter(course_code=course).order_by('datetime').first()
        first_assignment_date = first_assignment.datetime.strftime("%d.%m.%Y %H:%M") if first_assignment else ""

        # Берём первый тест курса
        quiz = Quiz.objects.filter(course=course).order_by('id').first()

        # Подсчёт общего количества занятий по курсу
        total_classes = Attendance.objects.filter(course=course).values_list('date', flat=True).distinct().count()

        for student in students:
            department_name = student.department.name if student.department else ""

            # Подсчёт оценки и даты сдачи теста
            score = ""
            submit_date = ""
            if quiz:
                answers = StudentAnswer.objects.filter(quiz=quiz, student=student)
                score_sum = answers.aggregate(total_marks=Sum('marks'))['total_marks'] or 0
                score = str(score_sum)

                last_answer = answers.order_by('-created_at').first()
                if last_answer and last_answer.created_at:
                    submit_date = last_answer.created_at.strftime("%d.%m.%Y %H:%M")

            # Подсчёт посещаемости
            attended_classes = Attendance.objects.filter(
                course=course,
                student=student,
                status=True  # предполагается BooleanField
            ).values_list('date', flat=True).distinct().count()
            attendance_stat = f"{attended_classes}/{total_classes}" if total_classes else "0/0"

            ws.append([
                department_name,
                course.name,
                course.code,
                student.name,
                student.email,
                first_assignment_date,
                score,
                submit_date,
                attendance_stat,
            ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="stat.xlsx"'
    wb.save(response)
    return response

def download_schedule_excel(request, course_code):
    student_id = request.session.get('student_id')
    if not student_id:
        return HttpResponse("Пожалуйста, войдите в систему как студент.", status=403)

    student = get_object_or_404(Student, student_id=student_id)
    course = get_object_or_404(Course, code=course_code)

    all_dates = Attendance.objects.filter(course=course).values_list('date', flat=True).distinct().order_by('date')
    student_attendance = Attendance.objects.filter(course=course, student=student)
    attendance_dict = {att.date: att.status for att in student_attendance}

    today = datetime.date.today()

    wb = Workbook()
    ws = wb.active
    ws.title = "Расписание посещаемости"

    ws.append(["Курс:", f"{course.department}-{course.code} : {course.name}"])
    ws.append(["Количество занятий:", len(all_dates)])
    ws.append([])

    ws.append(["Дата занятия", "Статус посещения"])

    for d in all_dates:
        status_code = attendance_dict.get(d)
        if status_code is None:
            if d > today:
                status = "Ещё не проведено"
            else:
                status = "Не посещал"
        elif status_code:
            status = "Посетил"
        else:
            status = "Не посетил"

        ws.append([d.strftime("%d.%m.%Y"), status])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    filename = f"timesheet_{course.code}_{student.student_id}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response

def my_requests(request):
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('std_login')
    student = get_object_or_404(Student, student_id=student_id)
    requests = CourseRequest.objects.filter(student=student).select_related('course').order_by('-created_at')
    return render(request, 'main/my_requests.html', {'requests': requests, 'student': student})

def submit_course_request(request, course_code):
    student_id = request.session.get('student_id')
    if not student_id:
        messages.error(request, "Пожалуйста, войдите в систему.")
        return redirect('std_login')

    student = get_object_or_404(Student, student_id=student_id)
    course = get_object_or_404(Course, code=course_code)

    # Проверяем, есть ли уже заявка на этот курс
    existing_request = CourseRequest.objects.filter(student=student, course=course).first()
    if existing_request:
        messages.info(request, "Вы уже подали заявку на этот курс.")
    else:
        CourseRequest.objects.create(student=student, course=course)
        messages.success(request, "Заявка успешно подана.")

    return redirect('my_requests')


