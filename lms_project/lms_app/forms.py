from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Course, Submission, Post, Module, Lesson, Quiz, Question, Assignment, LessonContent

class SignupForm(UserCreationForm):
    role = forms.ChoiceField(choices=Profile.USER_ROLES)
    bio = forms.CharField(widget=forms.Textarea, required=False)
    skills = forms.CharField(required=False)
    interests = forms.CharField(required=False)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                bio=self.cleaned_data['bio'],
                skills=self.cleaned_data['skills'],
                interests=self.cleaned_data['interests']
            )
        return user

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role', 'bio', 'skills', 'interests', 'photo']

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'category', 'difficulty']

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'order']

class LessonContentForm(forms.ModelForm):
    class Meta:
        model = LessonContent
        fields = ['content_type', 'value', 'order']
        widgets = {
            'value': forms.Textarea(attrs={'placeholder': 'Enter content for this lesson...'}),
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'total_marks']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['correct_answer']

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file_url']

class GradeForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['grade']

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content']