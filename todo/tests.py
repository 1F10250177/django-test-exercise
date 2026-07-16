from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.utils import timezone

from todo.models import Task


class SampleTestCase(TestCase):
    def test_sample1(self):
        self.assertEqual(1 + 2, 3)


class TaskModelCase(TestCase):
    def test_create_task1(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        task = Task(title='task1', due_at=due)
        task.save()

        task = Task.objects.get(pk=task.pk)
        self.assertEqual(task.title, 'task1')
        self.assertFalse(task.completed)
        self.assertEqual(task.due_at, due)

    def test_create_task2(self):
        task = Task(title='task2')
        task.save()

        task = Task.objects.get(pk=task.pk)
        self.assertEqual(task.title, 'task2')
        self.assertFalse(task.completed)
        self.assertEqual(task.due_at, None)

    def test_create_task_with_priority(self):
        user = User.objects.create_user(username='priority-user', password='testpass123')
        client = Client()
        client.force_login(user)
        client.post('/', {
            'title': 'High priority task',
            'priority': '1',
        })

        task = Task.objects.get(title='High priority task')
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.owner, user)

    def test_is_overdue_future(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        current = timezone.make_aware(datetime(2024, 6, 30, 0, 0, 0))
        task = Task(title='task1', due_at=due)
        task.save()

        self.assertFalse(task.is_overdue(current))

    def test_is_overdue_past(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        current = timezone.make_aware(datetime(2024, 7, 1, 0, 0, 0))
        task = Task(title='task1', due_at=due)
        task.save()

        self.assertTrue(task.is_overdue(current))

    def test_is_overdue_none(self):
        current = timezone.make_aware(datetime(2024, 6, 30, 0, 0, 0))
        task = Task(title='task1', due_at=None)
        task.save()

        self.assertFalse(task.is_overdue(current))


class AuthenticationTestCase(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = Client().get('/')

        self.assertRedirects(response, '/accounts/login/?next=/')

    def test_signup_logs_user_in(self):
        client = Client()
        response = client.post('/accounts/signup/', {
            'username': 'new-user',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })

        self.assertRedirects(response, '/')
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertTrue(User.objects.filter(username='new-user').exists())

    def test_user_cannot_see_another_users_tasks(self):
        user = User.objects.create_user(username='user-a', password='testpass123')
        other_user = User.objects.create_user(username='user-b', password='testpass123')
        own_task = Task.objects.create(title='Own task', owner=user)
        other_task = Task.objects.create(title='Other task', owner=other_user)
        client = Client()
        client.force_login(user)

        response = client.get('/?status=all')

        self.assertContains(response, own_task.title)
        self.assertNotContains(response, other_task.title)

    def test_user_cannot_access_another_users_task(self):
        user = User.objects.create_user(username='user-a', password='testpass123')
        other_user = User.objects.create_user(username='user-b', password='testpass123')
        task = Task.objects.create(title='Private task', owner=other_user)
        client = Client()
        client.force_login(user)

        response = client.get('/{}/'.format(task.pk))

        self.assertEqual(response.status_code, 404)

    def test_logout_requires_login_again(self):
        user = User.objects.create_user(username='logout-user', password='testpass123')
        client = Client()
        client.force_login(user)

        response = client.post('/accounts/logout/')

        self.assertRedirects(response, '/accounts/login/')
        self.assertRedirects(client.get('/'), '/accounts/login/?next=/')


class TodoViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_index_get(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(len(response.context['tasks']), 0)

    def test_index_post(self):
        data = {'title': 'Test Task', 'due_at': '2024-06-30 23:59:59'}
        response = self.client.post('/', data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(len(response.context['tasks']), 1)

    def test_index_post_without_due_at(self):
        data = {'title': 'Test Task', 'due_at': ''}
        response = self.client.post('/', data)

        task = Task.objects.get(title='Test Task')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(task.due_at, None)
        self.assertEqual(task.owner, self.user)

    def test_toggle_completed_hides_task_from_active_list(self):
        task = Task.objects.create(title='Task to complete', owner=self.user)

        response = self.client.post('/{}/toggle-completed/'.format(task.pk))

        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(task.completed)
        self.assertNotContains(self.client.get('/'), task.title)
        self.assertContains(self.client.get('/?status=completed'), task.title)

    def test_toggle_completed_back_to_active(self):
        task = Task.objects.create(
            title='Completed task',
            completed=True,
            owner=self.user,
        )

        response = self.client.post('/{}/toggle-completed/'.format(task.pk))

        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(task.completed)
        self.assertContains(self.client.get('/'), task.title)

    def test_index_get_order_post(self):
        task1 = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
            owner=self.user,
        )
        task2 = Task.objects.create(
            title='task2',
            due_at=timezone.make_aware(datetime(2024, 8, 1)),
            owner=self.user,
        )
        response = self.client.get('/?order=post')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(response.context['tasks'][0], task2)
        self.assertEqual(response.context['tasks'][1], task1)

    def test_index_get_order_due(self):
        task1 = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
            owner=self.user,
        )
        task2 = Task.objects.create(
            title='task2',
            due_at=timezone.make_aware(datetime(2024, 8, 1)),
            owner=self.user,
        )
        response = self.client.get('/?order=due')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(response.context['tasks'][0], task1)
        self.assertEqual(response.context['tasks'][1], task2)

    def test_detail_get_success(self):
        task = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
            owner=self.user,
        )
        response = self.client.get('/{}/'.format(task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/detail.html')
        self.assertEqual(response.context['task'], task)

    def test_detail_get_fail(self):
        response = self.client.get('/1/')

        self.assertEqual(response.status_code, 404)

    def test_edit_post_success(self):
        task = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
            owner=self.user,
        )
        data = {
            'title': 'updated task',
            'due_at': '2024-07-02 12:30:00',
            'priority': '1',
            'completed': 'on',
        }
        response = self.client.post('/{}/edit/'.format(task.pk), data)

        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/{}/'.format(task.pk))
        self.assertEqual(task.title, 'updated task')
        self.assertEqual(task.due_at, timezone.make_aware(datetime(2024, 7, 2, 12, 30)))
        self.assertEqual(task.priority, 1)
        self.assertTrue(task.completed)

    def test_edit_post_without_due_at_and_completed(self):
        task = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
            completed=True,
            owner=self.user,
        )
        data = {
            'title': 'updated task',
            'due_at': '',
        }
        response = self.client.post('/{}/edit/'.format(task.pk), data)

        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/{}/'.format(task.pk))
        self.assertEqual(task.title, 'updated task')
        self.assertEqual(task.due_at, None)
        self.assertFalse(task.completed)

    def test_edit_post_fail(self):
        data = {
            'title': 'updated task',
            'due_at': '',
        }
        response = self.client.post('/1/edit/', data)

        self.assertEqual(response.status_code, 404)

    def test_delete_get_success(self):
        task = Task.objects.create(title='task1', owner=self.user)
        response = self.client.get('/{}/delete'.format(task.pk))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.filter(pk=task.pk).count(), 0)
        self.assertEqual(response.url, '/')

    def test_delete_get_fail(self):
        response = self.client.get('/1/delete')

        self.assertEqual(response.status_code, 404)
