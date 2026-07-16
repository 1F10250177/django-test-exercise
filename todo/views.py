from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404, HttpResponseNotAllowed
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from todo.models import Task


# Create your views here.
def index(request):
    if request.method == 'POST':
        due_at_str = request.POST.get('due_at')
        if due_at_str:
            due_at = make_aware(parse_datetime(due_at_str))
        else:
            due_at = None
        task = Task(title=request.POST['title'],
                    due_at=due_at,
                    priority=request.POST.get('priority', 2))
        task.save()

    status = request.GET.get('status', 'active')
    tasks = Task.objects.all()
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


def detail(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    
    context = {
        'task': task,
    }
    return render(request, 'todo/detail.html', context)


def edit(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    
    if request.method == 'POST':
        task.title = request.POST['title']
        if request.POST.get('due_at'):
            task.due_at = make_aware(parse_datetime(request.POST['due_at']))
        else:
            task.due_at = None
        if request.POST.get('priority'):
            task.priority = request.POST.get('priority')
        if request.POST.get('completed'):
            task.completed = True
        else:
            task.completed = False
        task.save()
        return redirect('detail', task_id=task.id)
    
    context = {
        'task': task,
    }
    return render(request, 'todo/edit.html', context)


def toggle_completed(request, task_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    task = get_object_or_404(Task, pk=task_id)
    task.completed = not task.completed
    task.save(update_fields=['completed'])
    return redirect('index')

def delete(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    task.delete()
    return redirect(index)
