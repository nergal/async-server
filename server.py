#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import re
import socket
import sys
import thread
import select

import pdb

HOST = 'localhost'
PORT = 8809

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
	sock.bind((HOST, PORT))
except socket.error, msg:
	print msg
	sys.exit(1)

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 20)
sock.setblocking(1)
sock.listen(True)

query = re.compile(r'(?P<type>GET|POST|HEAD|DELETE|PUT) (?P<addr>[^ ]+) (?P<proto>HTTP\/1.(?:1|0))', flags=re.U+re.M+re.S+re.I)

def makeResponse(data, status = 200, proto = 'HTTP/1.0'):
	date = datetime.utcnow().ctime()
	length = len(data)
	
	response = []
	if status == 200:
		response.append('%s 200 OK' % proto)
	elif status == 404:
		response.append('%s 404 Not found' % proto)
	else:
		response.append('%s 503 Service temporary unavailable' % proto)
	response.append('Date: %s GMT' % date)
	response.append('Server: Nergal/Python')
	response.append('Last-Modified: %s GMT' % date)
	response.append('Content-Language: ru')
	response.append('Content-Type: text/html; charset=utf-8')
	response.append('Content-Length: %d' % length)
	response.append('Connection:keep-alive')
	#response.append('Connection: closed')
	response.append('\r\n')
	response.append(data)
	response.append('\r\n')
	
	return "\r\n".join(response)

def proceed(conn):
	global query

	poll = select.poll()	
	poll.register(conn, select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLOUT)
	
	request = None
	
	while True:
		events = poll.poll(0.0)
		
		for fd, event in events:
			if event & select.POLLIN or event & select.POLLPRI:
				data = conn.recv(1024)
				request = data.split('\r\n')
			if event & select.POLLERR:
				print 'POLLERR'
				conn.close()
				sys.exit(1)
			if event & select.POLLHUP:
				print 'POLLHUP'
				conn.close()
				sys.exit(1)
			if event & select.POLLOUT:
				if request is None:
					response = makeResponse('<h1>Not found</h1>', 404)
				else:
					response = _proceed(request)
				conn.send(response)
				conn.close()
				return
	
	conn.close()
	thread.exit()
	
def _proceed(request):		
	response = makeResponse('<h1>test</h1>')
	return response

while True:
	conn, addr = sock.accept()
	thread.start_new_thread(proceed, (conn,))