import requests
class RequestsTest:
	def get_127_0_0_1_8000(self):		
		headers = {'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjU3NjIzMzAxLCJpYXQiOjE2NTY3NTkzMDEsImp0aSI6IjIwYzJiZDdmMzMyNjRkYzA4YTI2OTYwM2JiZGQzZGNlIiwidXNlcl9pZCI6MX0.3pfInk0lQjc8cUAXGOGIPCqyYN499PlhHlGf1gVzY9o', 'X-CSRFToken': 'r2uDCpZU2Z9peKb4AzePUPpZN9vjRlUQCWDcE0opBLP7gE3MbCcEgjpva02Iodcm'}
		cookies = {}
		response = requests.get('http://127.0.0.1:8000/task/comments', headers=headers, cookies=cookies)
		print(response.text)
	def post_127_0_0_1_8000(self):		
		headers = {'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjU3NjIzMzAxLCJpYXQiOjE2NTY3NTkzMDEsImp0aSI6IjIwYzJiZDdmMzMyNjRkYzA4YTI2OTYwM2JiZGQzZGNlIiwidXNlcl9pZCI6MX0.3pfInk0lQjc8cUAXGOGIPCqyYN499PlhHlGf1gVzY9o', 'Content-Type': 'application/json', 'X-CSRFToken': 'r2uDCpZU2Z9peKb4AzePUPpZN9vjRlUQCWDcE0opBLP7gE3MbCcEgjpva02Iodcm'}
		cookies = {}
		data = {'posted_on': 1, 'body': 'stringg'}
		response = requests.post('http://127.0.0.1:8000/task/comments', headers=headers, cookies=cookies, data=data)
		print(response.text)
	def call_all(self):
		self.get_127_0_0_1_8000()
		self.post_127_0_0_1_8000()

if __name__ == '__main__': 
	RequestsTest().call_all()
