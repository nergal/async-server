#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os.path
import re
from urlparse import urlparse
import socket
import sys
import thread
import select
import tempfile
import subprocess

# import pdb

HOST = 'localhost'
PORT = 8808

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def getConnect(sock, host, port):
	try:
		sock.bind((host, port))
		return True
	except socket.error, msg:
		return False

while not getConnect(sock, HOST, PORT):
	PORT+= 1

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 20)
sock.setblocking(1)
sock.listen(True)

print "Server started at %s:%d" % (HOST, PORT)

query = re.compile(r'(?P<type>GET|POST|HEAD|DELETE|PUT) (?P<addr>[^ ]+) (?P<proto>HTTP\/1.(?:1|0))', flags=re.U+re.M+re.S+re.I)

def makeResponse(data, status = 200, proto = 'HTTP/1.0', raw = False, chuncked=False):
	length = len(data)
	
	response = []
	if status == 200:
		response.append('%s 200 OK' % proto)
	elif status == 404:
		response.append('%s 404 Not found' % proto)
	else:
		response.append('%s 503 Service temporary unavailable' % proto)
	
	date = datetime.utcnow().ctime()
	response.append('Date: %s GMT' % date)
	response.append('Server: Nergal/Python')
	response.append('Content-Length: %d' % length)
	response.append('Connection: keep-alive')
	
	if chuncked:
		response.append('Transfer-Encoding: chunked')
		response.append('Last-Modified: %s GMT' % date)
	else:
		response.append('Content-Language: ru')
		response.append('Content-Type: text/html; charset=utf-8')
	
	
	if not raw:
		response.append('\r\n')
	
	response.append(data)
	response.append('\r\n\r\n')
	
	return "\r\n".join(response)

def proceed(conn):
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
				response = None
				
				if request is None:
					response = makeResponse('<h1>Not found</h1>', 404)
				else:
					try:
						response = _proceed(request)
					except Exception, e:
						print "Something bag happening in this world, it said '%s'" % e
						return
				conn.send(response)
				conn.close()
				return
	
	conn.close()
	thread.exit()
	
def run(filename, query, type):
	output = None
	'''
		QUERY_STRING       $query_string;
		REQUEST_METHOD     $request_method;
		CONTENT_TYPE       $content_type;
		CONTENT_LENGTH     $content_length;

		REQUEST_URI        $request_uri;
		DOCUMENT_URI       $document_uri;
		DOCUMENT_ROOT      $document_root;
		SERVER_PROTOCOL    $server_protocol;

		REMOTE_ADDR        $remote_addr;
		REMOTE_PORT        $remote_port;
		SERVER_ADDR        $server_addr;
		SERVER_PORT        $server_port;
		SERVER_NAME        $server_name;
	'''
	
	env = {
		'SCRIPT_FILENAME': filename,
		'REDIRECT_STATUS': '200',
		'GATEWAY_INTERFACE':  'CGI/1.1',
		'SERVER_SOFTWARE': 'Nergal/Python',
		'QUERY_STRING': query,
		'REQUEST_METHOD': type,
	}
	
	data = tempfile.TemporaryFile(mode='wr+b')
	php = subprocess.call(
		["/usr/bin/php-cgi"],
		env=env,
		stdout=data,
		stderr=data,
		stdin=data
	)
	
	data.seek(0)
	output = data.read()

	data.close()

	return output
	
	
def _proceed(request):
	global query
	heading = request[0]
	
	match = query.match(heading)
	if (match):
		uri = match.group('addr')
		# Хуйня какая-то...
		date = datetime.utcnow().ctime()
		print "%s %s %s" % (date, match.group('type'), match.group('addr'))
		uri = urlparse(uri)
		
		path = uri.path
		if path[-1] == '/':
			path+= 'index.php'
		
		if path[0] == '/':
			path = path[1:]
		
		filename = os.path.abspath(path)
		
		if not os.path.exists(filename):
			raise Exception('File %s not exists' % uri.path)
		
		chuncked = False
		for header in request:
			if header == 'Accept: */*':
				chuncked = True
		
		if path[-4:] == '.php':
			output = run(filename, uri.query, match.group('type'))
			return makeResponse(output, 200, raw=True, chuncked=chuncked)
	else:
		raise Exception('Bad query')
	
	response = makeResponse('<h1>Not a php file</h1>', 404)
	return response

while True:
	conn, addr = sock.accept()
	thread.start_new_thread(proceed, (conn,))