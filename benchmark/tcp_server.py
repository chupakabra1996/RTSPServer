#!/usr/bin/env python

import socket
import sys
from time import sleep
import subprocess32 as subprocess
import json

BENCH_CONFIG_FILE = 'benchmark.json'
BUFFER_SIZE = 1024
HOST = '0.0.0.0'
PORT = 15555

SERVER_START_CMD_PATTERN = "./LiveVideoStream --trial={} -t camera -s rare --out-width={} --out-height={}" \
                           " --vbv-bufsize={} --udp={} --bitrate={} --out-fps={}"

CLIENT_CMD_PATTERN = 'openRTSP -V -f {} -w {} -h {} -Q -n -d {} -F trial_{}_ rtsp://10.42.0.1:8554/camera'


def set_keep_alive(sock, after_idle_sec=30, interval_sec=30, max_fails=10):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def wait_for_data(sock, sleep_sec=1):
    data = ''
    while data == '':
        data = sock.recv(BUFFER_SIZE)
        sleep(sleep_sec)
    return data


def load_test_config(filename):
    with open(filename) as infile:
        return json.load(infile)


def bind_sock(sock):
    try:
        sock.bind((HOST, PORT))
    except socket.error as err:
        print "Bind failed. Error code : " + str(err)
        sys.exit()


if __name__ == "__main__":

    # create a server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind a socket to the address
    bind_sock(server_socket)

    server_socket.listen(1)

    print "Socket is listening..."

    set_keep_alive(server_socket)

    # wait for clients
    client_connection, addr = server_socket.accept()

    print "Client has connected: ", str(addr)

    client_data = ''

    # load benchmark's params
    trials = load_test_config(BENCH_CONFIG_FILE)

    # open the log file
    with open('server_output.log', 'wb') as logfile:

        for trial in trials['benchmark']:

            try:

                server_cmd = SERVER_START_CMD_PATTERN.format(trial['trial'], trial['width'], trial['height'],
                                                             trial['bufsize'], trial['udp'], trial['bitrate'],
                                                             trial['framerate'])

                print "Starting the server... : '{}'".format(server_cmd)

                client_cmd = CLIENT_CMD_PATTERN.format(trial['framerate'], trial['width'], trial['height'], 180,
                                                       trial['trial'])

                # open the server process with the specified logfile
                video_server_process = subprocess.Popen(server_cmd.split(), stdout=logfile, stderr=logfile)

                sleep(10)  # waiting for the server to be ready to accept connections

                print "Sending command to client ..."

                client_connection.sendall(client_cmd)

                print "Waiting for client's cmd to stop the server ..."

                client_data = wait_for_data(client_connection)

                # stop the server
                video_server_process.terminate()

                sleep(5)  # wait for the server to stop

            except socket.error:
                print "Error occurred:", str(socket.error)
                break

    # send a kill cmd to the client to be stopped
    client_connection.sendall("KILL")

    sleep(5)  # wait for the client to stop

    # close resources
    client_connection.close()
    server_socket.close()
