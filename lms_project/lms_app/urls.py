from django.urls import path
from . import views

urlpatterns = [
    # General & User URLs
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Student URLs
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('courses/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('assignment/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('certificates/', views.certificate_list, name='certificate_list'),

    # Instructor URLs
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('instructor/courses/create/', views.create_course, name='create_course'),
    path('instructor/courses/<int:course_id>/manage/', views.manage_course, name='manage_course'),
    path('instructor/modules/add/<int:course_id>/', views.add_module, name='add_module'),
    path('instructor/lessons/add/<int:module_id>/', views.add_lesson, name='add_lesson'),
    path('instructor/quizzes/add/<int:lesson_id>/', views.add_quiz, name='add_quiz'),
    path('instructor/questions/add/<int:quiz_id>/', views.add_question, name='add_question'),
    path('instructor/assignments/add/<int:lesson_id>/', views.add_assignment, name='add_assignment'),
    path('instructor/submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('instructor/analytics/<int:course_id>/', views.analytics_dashboard, name='analytics_dashboard'),
    path('instructor/quiz/<int:quiz_id>/results/', views.quiz_results_for_instructor, name='quiz_results_for_instructor'),
    path('instructor/assignment/<int:assignment_id>/submissions/', views.assignment_submissions_for_instructor, name='assignment_submissions_for_instructor'),

    # Forum URLs
    path('courses/<int:course_id>/forum/', views.forum_view, name='forum_view'),
    path('courses/<int:course_id>/forum/create_post/', views.create_post, name='create_post'),
    path('api/quiz-performance/', views.quiz_performance_api, name='quiz_performance_api'),

]