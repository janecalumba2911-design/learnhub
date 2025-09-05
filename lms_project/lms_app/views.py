from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Avg, Sum
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Prefetch

from .models import *
from .forms import *
from .models import Forum, Post

# --- Helper Function for Decorator ---
def is_instructor(user):
    return user.is_authenticated and user.profile.role == 'Instructor'


def home(request):
    # Get 6 random courses
    courses = Course.objects.order_by('?')[:6]

    return render(request, 'home.html', {
        'courses': courses,
    })


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'profile.html', {'profile': profile})

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})

@login_required
def dashboard_view(request):
    if request.user.profile.role == 'Instructor':
        return redirect('instructor_dashboard')

    enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
    certificates = Certificate.objects.filter(user=request.user).select_related('course')

    # Corrected: follow the forum -> course relationship
    recent_forum_posts = Post.objects.filter(
        forum__course__in=[en.course for en in enrollments]
    ).select_related('forum', 'user').order_by('-created_at')[:2]

    return render(request, 'student_dashboard.html', {
        'enrollments': enrollments,
        'certificates': certificates,
        'recent_forum_posts': recent_forum_posts
    })



@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = Module.objects.filter(course=course).order_by('order')
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    return render(request, 'course_detail.html', {'course': course, 'modules': modules, 'is_enrolled': is_enrolled})

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        Enrollment.objects.create(user=request.user, course=course)
        analytics, created = Analytics.objects.get_or_create(course=course)
        analytics.total_enrolled += 1
        analytics.save()
        Notification.objects.create(user=request.user, message=f'You have enrolled in {course.title}.', notification_type='enrollment')
    return redirect('course_detail', course_id=course_id)

@login_required
def lesson_detail(request, course_id, module_id, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__id=module_id, module__course__id=course_id)
    course = lesson.module.course

    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return HttpResponseForbidden("You must be enrolled in this course to view this lesson.")

    lesson_progress, created = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    lesson_progress.completed = True
    lesson_progress.completion_date = timezone.now()
    lesson_progress.save()

    enrollment = Enrollment.objects.get(user=request.user, course=course)
    lessons_in_course = Lesson.objects.filter(module__course=course).count()
    completed_lessons = LessonProgress.objects.filter(user=request.user, lesson__module__course=course, completed=True).count()

    if lessons_in_course > 0:
        new_progress = int((completed_lessons / lessons_in_course) * 100)
        enrollment.progress = new_progress
        enrollment.save()

    if new_progress >= 100 and not enrollment.is_completed:
        enrollment.is_completed = True
        enrollment.save()
        Certificate.objects.create(user=request.user, course=course)
        Notification.objects.create(user=request.user, message=f'Congratulations! You have completed the course {course.title} and earned a certificate.', notification_type='certificate')

    lesson_content = LessonContent.objects.filter(lesson=lesson).first()

    quiz = Quiz.objects.filter(lesson=lesson).first()
    assignment = Assignment.objects.filter(lesson=lesson).first()

    quiz_attempted = False
    if quiz:
        quiz_attempted = QuizAttempt.objects.filter(user=request.user, quiz=quiz).exists()

    assignment_submitted = False
    if assignment:
        assignment_submitted = Submission.objects.filter(student=request.user, assignment=assignment).exists()

    context = {
        'lesson': lesson,
        'lesson_content': lesson_content, # Changed to use the fetched object
        'quiz': quiz,
        'assignment': assignment,
        'quiz_attempted': quiz_attempted,
        'assignment_submitted': assignment_submitted,
    }
    return render(request, 'lesson_detail.html', context)

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    course = quiz.lesson.module.course

    if request.method == 'POST':
        score = 0
        total_questions = quiz.question_set.count()

        for question in quiz.question_set.all():
            given_answer = request.POST.get(f'question_{question.id}')
            if given_answer == question.correct_answer:
                score += 1

        QuizAttempt.objects.create(user=request.user, quiz=quiz, score=score)

        return render(request, 'quiz_results.html', {'score': score, 'total': total_questions, 'course_id': course.id})

    questions = quiz.question_set.all()
    return render(request, 'take_quiz.html', {'quiz': quiz, 'questions': questions})

@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = request.user
            submission.assignment = assignment
            submission.save()
            return redirect('lesson_detail', course_id=assignment.lesson.module.course.id, module_id=assignment.lesson.module.id, lesson_id=assignment.lesson.id)
    else:
        form = SubmissionForm()
    return render(request, 'submit_assignment.html', {'form': form, 'assignment': assignment})

@login_required
def certificate_list(request):
    certificates = Certificate.objects.filter(user=request.user)
    return render(request, 'certificate_list.html', {'certificates': certificates})



from django.db.models import Count, Avg
from django.utils.timezone import now
from datetime import timedelta

@login_required
@user_passes_test(is_instructor)
def instructor_dashboard(request):
    courses = Course.objects.filter(created_by=request.user)

    # Stats
    total_courses = courses.count()
    total_students = Enrollment.objects.filter(course__in=courses).count()
    avg_completion = Enrollment.objects.filter(course__in=courses).aggregate(models.Avg('progress'))['progress__avg'] or 0
    avg_quiz_score = QuizAttempt.objects.filter(quiz__lesson__module__course__in=courses).aggregate(models.Avg('score'))['score__avg'] or 0

    # Recent enrollments & submissions & posts & reviews & certificates
    recent_enrollments = Enrollment.objects.filter(course__in=courses).select_related('user', 'course').order_by('-enrolled_at')[:5]
    pending_submissions = Submission.objects.filter(assignment__lesson__module__course__in=courses, grade__isnull=True).select_related('student', 'assignment')[:5]
    recent_posts = Post.objects.filter(forum__course__in=courses).select_related('user', 'forum').order_by('-created_at')[:5]
    recent_reviews = CourseReview.objects.filter(course__in=courses).select_related('user', 'course').order_by('-created_at')[:5]
    recent_certificates = Certificate.objects.filter(course__in=courses).select_related('user', 'course').order_by('-issued_at')[:5]

    # --- Dynamic Enrollment Chart (Last 6 Months) ---
    today = now().date()
    months = []
    enroll_counts = []
    for i in range(5, -1, -1):
        month_start = today.replace(day=1) - timedelta(days=i*30)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_label = month_start.strftime('%b')
        months.append(month_label)
        count = Enrollment.objects.filter(course__in=courses, enrolled_at__month=month_start.month).count()
        enroll_counts.append(count)

    # --- Dynamic Quiz Performance (0-50%, 50-75%, 75-100%) ---
    quiz_data = [0, 0, 0]
    attempts = QuizAttempt.objects.filter(quiz__lesson__module__course__in=courses)
    for a in attempts:
        if a.score < 50:
            quiz_data[0] += 1
        elif 50 <= a.score < 75:
            quiz_data[1] += 1
        else:
            quiz_data[2] += 1

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'avg_completion': round(avg_completion, 2),
        'avg_quiz_score': round(avg_quiz_score, 2),
        'recent_enrollments': recent_enrollments,
        'pending_submissions': pending_submissions,
        'recent_posts': recent_posts,
        'recent_reviews': recent_reviews,
        'recent_certificates': recent_certificates,


        "enrollment_labels" : months, 
        'enrollment_data': enroll_counts,                

        # Quiz chart
        'quiz_labels': ["0-50%", "50-75%", "75-100%"],
        'quiz_data': quiz_data,
    }

    return render(request, 'instructor_dashboard.html', context)

# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(is_instructor)
def quiz_performance_api(request):
    courses = Course.objects.filter(created_by=request.user)
    quiz_data = [0, 0, 0]
    attempts = QuizAttempt.objects.filter(quiz__lesson__module__course__in=courses)

    for a in attempts:
        if a.score < 50:
            quiz_data[0] += 1
        elif 50 <= a.score < 75:
            quiz_data[1] += 1
        else:
            quiz_data[2] += 1

    return JsonResponse({
        'quiz_labels': ["0-50%", "50-75%", "75-100%"],
        'quiz_data': quiz_data
    })







@login_required
@user_passes_test(is_instructor)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            Forum.objects.create(course=course, title=f'{course.title} Forum')
            return redirect('manage_course', course_id=course.id)
    else:
        form = CourseForm()
    return render(request, 'create_course.html', {'form': form})

@login_required
@user_passes_test(is_instructor)
def manage_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, created_by=request.user)
    modules = Module.objects.filter(course=course).order_by('order')

    return render(request, 'manage_course.html', {'course': course, 'modules': modules})

@login_required
@user_passes_test(is_instructor)
def add_module(request, course_id):
    course = get_object_or_404(Course, id=course_id, created_by=request.user)
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            return redirect('manage_course', course_id=course.id)
    else:
        form = ModuleForm()
    return render(request, 'add_module.html', {'form': form, 'course': course})

@login_required
@user_passes_test(is_instructor)
def add_lesson(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__created_by=request.user)
    if request.method == 'POST':
        lesson_form = LessonForm(request.POST)
        content_form = LessonContentForm(request.POST)
        if lesson_form.is_valid() and content_form.is_valid():
            lesson = lesson_form.save(commit=False)
            lesson.module = module
            lesson.save()

            content = content_form.save(commit=False)
            content.lesson = lesson
            content.save()

            return redirect('manage_course', course_id=module.course.id)
    else:
        lesson_form = LessonForm()
        content_form = LessonContentForm()

    context = {
        'lesson_form': lesson_form,
        'content_form': content_form,
        'module': module,
    }
    return render(request, 'add_lesson.html', context)

@login_required
@user_passes_test(is_instructor)
def add_quiz(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__created_by=request.user)
    if Quiz.objects.filter(lesson=lesson).exists():
        messages.error(request, "A quiz already exists for this lesson. You can only have one quiz per lesson.")
        return redirect('manage_course', course_id=lesson.module.course.id)

    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.lesson = lesson
            quiz.save()
            return redirect('add_question', quiz_id=quiz.id)
    else:
        form = QuizForm()
    return render(request, 'add_quiz.html', {'form': form, 'lesson': lesson})

@login_required
@user_passes_test(is_instructor)
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, lesson__module__course__created_by=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            return redirect('course_list')
    else:
        form = QuestionForm()
    return render(request, 'add_question.html', {'form': form, 'quiz': quiz})

@login_required
@user_passes_test(is_instructor)
def add_assignment(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__created_by=request.user)
    if Assignment.objects.filter(lesson=lesson).exists():
        messages.error(request, "An assignment already exists for this lesson. You can only have one assignment per lesson.")
        return redirect('manage_course', course_id=lesson.module.course.id)

    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.lesson = lesson
            assignment.save()
            return redirect('manage_course', course_id=lesson.module.course.id)
    else:
        form = AssignmentForm()
    return render(request, 'add_assignment.html', {'form': form, 'lesson': lesson})

@login_required
@user_passes_test(is_instructor)
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.assignment.lesson.module.course.created_by != request.user:
        return HttpResponseForbidden("You cannot grade this submission.")

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            return redirect('analytics_dashboard', course_id=submission.assignment.lesson.module.course.id)
    else:
        form = GradeForm(instance=submission)
    return render(request, 'grade_submission.html', {'form': form, 'submission': submission})

@login_required
@user_passes_test(is_instructor)
def analytics_dashboard(request, course_id):
    course = get_object_or_404(
        Course.objects.prefetch_related(
            'module_set__lesson_set__assignment_set',
            'module_set__lesson_set__quiz_set'
        ),
        id=course_id,
        created_by=request.user
    )

    analytics, created = Analytics.objects.get_or_create(course=course)

    total_enrolled = Enrollment.objects.filter(course=course).count()
    avg_progress = Enrollment.objects.filter(course=course).aggregate(Avg('progress'))['progress__avg']
    completion_rate = Enrollment.objects.filter(course=course, is_completed=True).count() / (total_enrolled or 1) * 100
    avg_quiz_score = QuizAttempt.objects.filter(quiz__lesson__module__course=course).aggregate(Avg('score'))['score__avg']

    analytics.total_enrolled = total_enrolled
    analytics.avg_progress = avg_progress or 0
    analytics.completion_rate = completion_rate
    analytics.avg_quiz_score = (avg_quiz_score or 0)
    analytics.save()

    submissions = Submission.objects.filter(assignment__lesson__module__course=course, grade__isnull=True)

    return render(request, 'analytics_dashboard.html', {'course': course, 'analytics': analytics, 'submissions': submissions})

@login_required
@user_passes_test(is_instructor)
def quiz_results_for_instructor(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, lesson__module__course__created_by=request.user)
    quiz_attempts = QuizAttempt.objects.filter(quiz=quiz).select_related('user')
    return render(request, 'instructor_quiz_results.html', {'quiz': quiz, 'quiz_results': quiz_attempts})

@login_required
@user_passes_test(is_instructor)
def assignment_submissions_for_instructor(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, lesson__module__course__created_by=request.user)
    submissions = Submission.objects.filter(assignment=assignment).order_by('-submitted_at')
    return render(request, 'instructor_assignment_submissions.html', {'assignment': assignment, 'submissions': submissions})

# --- Forum Views ---
@login_required
def forum_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    forum = get_object_or_404(Forum, course=course)
    posts = Post.objects.filter(forum=forum).order_by('-created_at')
    return render(request, 'forum.html', {'forum': forum, 'posts': posts})


@login_required
def create_post(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    forum = get_object_or_404(Forum, course=course)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.forum = forum
            post.save()
            return redirect('forum_view', course_id=course_id)
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form, 'course': course})