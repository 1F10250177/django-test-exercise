from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST # POSTリクエスト制限用に追加
import json 
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

    order = request.GET.get('order')
    if order == 'due':
        tasks = Task.objects.order_by('due_at')
    elif order == 'priority':
        tasks = Task.objects.order_by('priority', 'due_at')
    else:
        tasks = Task.objects.order_by('-posted_at')

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


def delete(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    task.delete()
    return redirect(index)


@require_POST
def update_task_order(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])

        for index_num, task_id in enumerate(task_ids):
            Task.objects.filter(id=task_id).update(order=index_num)
    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})