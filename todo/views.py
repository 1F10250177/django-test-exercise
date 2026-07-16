from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseNotAllowed
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from todo.models import Task


# Create your views here.
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()

    return render(request, 'todo/signup.html', {'form': form})


@login_required
def index(request):
    if request.method == 'POST':
        due_at_str = request.POST.get('due_at')
        if due_at_str:
            due_at = make_aware(parse_datetime(due_at_str))
        else:
            due_at = None
        task = Task(title=request.POST['title'],
                    due_at=due_at,
                    priority=request.POST.get('priority', 2),
                    owner=request.user)
        task.save()

    status = request.GET.get('status', 'active')
    tasks = Task.objects.filter(owner=request.user)
    if status == 'completed':
        tasks = tasks.filter(completed=True)
    elif status != 'all':
        tasks = tasks.filter(completed=False)

    order = request.GET.get('order')
    if order == 'due':
        tasks = tasks.order_by('due_at')
    elif order == 'priority':
        tasks = tasks.order_by('priority', 'due_at')
    else:
        tasks = tasks.order_by('-posted_at')

    context = {
        'tasks': tasks
    }
    return render(request, 'todo/index.html', context)


@login_required
def detail(request, task_id):
    task = get_object_or_404(Task, pk=task_id, owner=request.user)
    
    context = {
        'task': task,
    }
    return render(request, 'todo/detail.html', context)


@login_required
def edit(request, task_id):
    task = get_object_or_404(Task, pk=task_id, owner=request.user)
    
    if request.method == 'POST':
        if request.POST.get('title'):
            task.title = request.POST['title']
        if request.POST.get('due_at'):
            task.due_at = make_aware(parse_datetime(request.POST['due_at']))
        else:
            task.due_at = None
        if request.POST.get('priority'):
            task.priority = request.POST.get('priority')
        completed_value = request.POST.get('completed')
        if completed_value == 'on' or completed_value == 'off':
            task.completed = completed_value == 'on'
        else:
            task.completed = False
        task.save()
        return redirect('detail', task_id=task.id)
    
    context = {
        'task': task,
    }
    return render(request, 'todo/edit.html', context)


@login_required
def toggle_completed(request, task_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    task = get_object_or_404(Task, pk=task_id, owner=request.user)
    task.completed = not task.completed
    task.save(update_fields=['completed'])
    return redirect('index')

@login_required
def delete(request, task_id):
    task = get_object_or_404(Task, pk=task_id, owner=request.user)
    task.delete()
    return redirect(index)
