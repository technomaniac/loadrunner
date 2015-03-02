from datetime import datetime
import subprocess
import sys
import time
import csv
import re
import json
from multiprocessing import Queue, Process, cpu_count

start = time.time()
NUM_PROCS = cpu_count() * 16
CSV_HEADER = ['URL', 'Title', 'Load Time', 'Page Size', 'Total Requests', 'Total Images', 'Total CSS', 'Total JS']


def get_csv_row(data):
    return [data['url'], data['title'], data['load_time'], data['page_size'], data['total_requests'],
            data['total_images'], data['total_css'], data['total_js']]


class TheCollector(object):
    def __init__(self):
        self.max_load_time = -sys.maxint
        self.min_load_time = sys.maxint
        self.max_requests = -sys.maxint
        self.min_requests = sys.maxint
        self.max_page_size = -sys.maxint
        self.min_page_size = sys.maxint

        self.max_load_time_url = None
        self.min_load_time_url = None
        self.max_requests_url = None
        self.min_requests_url = None
        self.max_page_size_url = None
        self.min_page_size_url = None

        self.avg_requests = 0
        self.avg_load_time = 0
        self.avg_page_size = 0

        self.total_load_time = 0
        self.total_requests = 0
        self.total_page_size = 0

        self.counter = 0

        self.results = dict()

    def set_data(self, data):
        # print data
        self.total_load_time += data['load_time']
        self.total_requests += data['total_requests']
        self.total_page_size += data['page_size']
        self.counter += 1

        if data['load_time'] > self.max_load_time:
            self.max_load_time_url = data['url']
            self.max_load_time = data['load_time']

        if data['load_time'] < self.min_load_time:
            self.min_load_time_url = data['url']
            self.min_load_time = data['load_time']

        if data['total_requests'] > self.max_requests:
            self.max_requests = data['total_requests']
            self.max_requests_url = data['url']

        if data['total_requests'] < self.min_requests:
            self.min_requests = data['total_requests']
            self.min_requests_url = data['url']

        if data['page_size'] > self.max_page_size:
            self.max_page_size = data['page_size']
            self.max_page_size_url = data['url']

        if data['page_size'] < self.min_page_size:
            self.min_page_size = data['page_size']
            self.min_page_size_url = data['url']


    def get_avg_load_time(self):
        return float(self.total_load_time) / self.counter

    def get_avg_requests(self):
        return float(self.total_requests) / self.counter

    def get_avg_page_size(self):
        return float(self.total_page_size) / self.counter


class CSVReader(object):
    def __init__(self, numprocs, infile):
        self.numprocs = numprocs
        self.infile = open(infile)
        self.in_csvfile = csv.reader(self.infile)
        # self.ip = ip
        self.in_csvfile = csv.reader(self.infile)
        self.inq = Queue()


    def get_row(self):
        for i, row in enumerate(self.in_csvfile):
            # print row[0] + '\n'
            match = re.search(r'http://', row[0])
            if match:
                yield row[0]
            else:
                print "Line %s : Invalid url - %s" % (i + 1, row[0])
                sys.exit(1)

                # yield "STOP"

                # def set_inq(self):
                # self.inq.put(self.get_row())


# def get_phantom_data(url):
# args = ["phantomjs", "loadrunner.js", url]
# data = subprocess.check_output(args)
# try:
# # print data
# return json.loads(data)
# except:
# match = re.search(r'\{([^}]*)\}', data)
# data = '{' + match.group(1) + '}'
# # print data
# return json.loads(data)

def get_phantom_data(url):
    args = ["phantomjs", "loadrunner.js", url]
    data = subprocess.check_output(args)
    try:
        return json.loads(data)
    except Exception as e:
        print '\n%s URL - %s\n' % (e.message, url)
        match = re.search(r'\{([^}]*)\}', data)
        data = '{' + match.group(1) + '}'
        return json.loads(data)
        #return None


def test_runner(queue, url):
    data = get_phantom_data(url)
    # pprint.pprint(data)
    # print "\n\n"
    if data:
        queue.put(data)


def main(input_file, output_file):
    csv_reader = CSVReader(NUM_PROCS, input_file)
    queue = Queue()

    the_collector = TheCollector()

    fp = open(output_file, 'w')
    wr = csv.writer(fp, quoting=csv.QUOTE_ALL)
    wr.writerow(CSV_HEADER)

    process = []
    urls = 0

    for row in csv_reader.get_row():
        urls += 1
        # print '%s - %s' % (urls, row)
        p = Process(target=test_runner, args=(queue, row))
        process.append(p)

        if urls % NUM_PROCS == 0 and NUM_PROCS <= urls:
            for p in process:
                p.start()

            for p in process:
                p.join()

            for _ in xrange(NUM_PROCS):

                data = queue.get()

                if data:
                    the_collector.set_data(data)
                    wr.writerow(get_csv_row(data))

            process = []

            print '%s url processed...' % (urls)

    if process:
        for p in process:
            p.start()

        for p in process:
            p.join()

        print '%s url processed...' % (urls)

    # the_collector = TheCollector()
    #
    # fp = open(output_file, 'w')
    # wr = csv.writer(fp, quoting=csv.QUOTE_ALL)
    # wr.writerow(CSV_HEADER)

    i = 0
    size = queue.qsize()
    while True:
        if i == size:
            break
        data = queue.get()

        if data:
            the_collector.set_data(data)
            wr.writerow(get_csv_row(data))

        i += 1
        # print '%s rows written...' % (i)

    wr.writerow([''])
    wr.writerow(['Max Load Time : %s - %s' % (the_collector.max_load_time, the_collector.max_load_time_url)])
    wr.writerow(['Min Load Time : %s - %s' % (the_collector.min_load_time, the_collector.min_load_time_url)])
    wr.writerow(['Max Requests  : %s - %s' % (the_collector.max_requests, the_collector.max_requests_url)])
    wr.writerow(['Min Requests  : %s - %s' % (the_collector.min_requests, the_collector.min_requests_url)])
    wr.writerow(['Max Page Size : %s - %s' % (the_collector.max_page_size, the_collector.max_page_size_url)])
    wr.writerow(['Min Page Size : %s - %s' % (the_collector.min_page_size, the_collector.min_page_size_url)])
    wr.writerow([''])
    wr.writerow(['Average Load Time : %s' % the_collector.get_avg_load_time()])
    wr.writerow(['Average Requests  : %s' % the_collector.get_avg_requests()])
    wr.writerow(['Average Page Size : %s' % the_collector.get_avg_page_size()])
    wr.writerow([''])
    wr.writerow(['Elapsed Time      : %s' % (time.time() - start)])


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Please provide input file"
    else:
        output_file = sys.argv[1].split('.')[0] + '_output_' + datetime.now().strftime('%d-%m-%y_%H:%M') + '.csv'
        main(sys.argv[1], output_file)
        print "\n\nElapsed Time: %s" % (time.time() - start)
        print "Output File : %s" % output_file



# from datetime import datetime
# import pprint
# import subprocess
# import sys
# import time
# import csv
# import re
# import json
# from multiprocessing import Queue, Process, cpu_count
#
#
# start = time.time()
# NUM_PROCS = cpu_count() * 8
# CSV_HEADER = ['URL', 'Title', 'Load Time', 'Page Size', 'Total Requests', 'Total Images', 'Total CSS', 'Total JS']
#
#
# def get_csv_row(data):
# return [data['url'], data['title'], data['load_time'], data['page_size'], data['total_requests'],
# data['total_images'], data['total_css'], data['total_js']]
#
#
# class TheCollector(object):
# def __init__(self):
# self.max_load_time = -sys.maxint
# self.min_load_time = sys.maxint
# self.max_requests = -sys.maxint
# self.min_requests = sys.maxint
# self.max_page_size = -sys.maxint
# self.min_page_size = sys.maxint
#
# self.max_load_time_url = None
# self.min_load_time_url = None
# self.max_requests_url = None
# self.min_requests_url = None
# self.max_page_size_url = None
# self.min_page_size_url = None
#
# self.avg_requests = 0
# self.avg_load_time = 0
# self.avg_page_size = 0
#
# self.total_load_time = 0
# self.total_requests = 0
# self.total_page_size = 0
#
# self.counter = 0
#
# self.results = dict()
#
# def set_data(self, data):
# # print data
# self.total_load_time += data['load_time']
# self.total_requests += data['total_requests']
# self.total_page_size += data['page_size']
# self.counter += 1
#
# if data['load_time'] > self.max_load_time:
# self.max_load_time_url = data['url']
# self.max_load_time = data['load_time']
#
#         if data['load_time'] < self.min_load_time:
#             self.min_load_time_url = data['url']
#             self.min_load_time = data['load_time']
#
#         if data['total_requests'] > self.max_requests:
#             self.max_requests = data['total_requests']
#             self.max_requests_url = data['url']
#
#         if data['total_requests'] < self.min_requests:
#             self.min_requests = data['total_requests']
#             self.min_requests_url = data['url']
#
#         if data['page_size'] > self.max_page_size:
#             self.max_page_size = data['page_size']
#             self.max_page_size_url = data['url']
#
#         if data['page_size'] < self.min_page_size:
#             self.min_page_size = data['page_size']
#             self.min_page_size_url = data['url']
#
#
#     def get_avg_load_time(self):
#         return float(self.total_load_time) / self.counter
#
#     def get_avg_requests(self):
#         return float(self.total_requests) / self.counter
#
#     def get_avg_page_size(self):
#         return float(self.total_page_size) / self.counter
#
#
# class CSVReader(object):
#     def __init__(self, numprocs, infile, ip):
#         self.numprocs = numprocs
#         self.infile = open(infile)
#         self.in_csvfile = csv.reader(self.infile)
#         self.ip = ip
#         self.in_csvfile = csv.reader(self.infile)
#         self.inq = Queue()
#
#
#     def get_row(self):
#         for i, row in enumerate(self.in_csvfile):
#             print row[0] + '\n'
#             match = re.search(r'http://', row[0])
#             if match:
#                 yield row[0]
#             else:
#                 yield 'http://' + self.ip + row[0]
#
#                 # yield "STOP"
#
#                 # def set_inq(self):
#                 # self.inq.put(self.get_row())
#
#
# # def get_phantom_data(url):
# # args = ["phantomjs", "loadrunner.js", url]
# # data = subprocess.check_output(args)
# # try:
# # # print data
# # return json.loads(data)
# # except:
# # match = re.search(r'\{([^}]*)\}', data)
# # data = '{' + match.group(1) + '}'
# # # print data
# # return json.loads(data)
#
# def get_phantom_data(url):
#     args = ["phantomjs", "loadrunner.js", url]
#     try:
#         data = subprocess.check_output(args)
#         return json.loads(data)
#     except Exception as e:
#         print '\n%s URL - %s\n' % (e.message, url)
#         # match = re.search(r'\{([^}]*)\}', data)
#         # data = '{' + match.group(1) + '}'
#         # print data
#         return None
#
#
# def test_runner(queue, url):
#     data = get_phantom_data(url)
#     pprint.pprint(data)
#     print "\n\n"
#     if data:
#         queue.put(data)
#
#
# def main(input_file, output_file):
#     csv_reader = CSVReader(NUM_PROCS, input_file, '50.116.43.18')
#     queue = Queue()
#
#     process = []
#     urls = 0
#
#     for row in csv_reader.get_row():
#         urls += 1
#         # print '%s - %s' % (urls, row)
#         p = Process(target=test_runner, args=(queue, row))
#         process.append(p)
#
#         if urls % NUM_PROCS == 0:
#             for p in process:
#                 p.start()
#
#             for p in process:
#                 p.join()
#
#             process = []
#
#             print '%s url processed...' % (urls)
#
#     if process:
#         for p in process:
#             p.start()
#
#         for p in process:
#             p.join()
#
#         print '%s url processed...' % (urls)
#
#     the_collector = TheCollector()
#
#     fp = open(output_file, 'w')
#     wr = csv.writer(fp, quoting=csv.QUOTE_ALL)
#     wr.writerow(CSV_HEADER)
#
#     i = 0
#     size = queue.qsize()
#     while True:
#         if i == size:
#             break
#         data = queue.get()
#
#         if data:
#             the_collector.set_data(data)
#             wr.writerow(get_csv_row(data))
#
#         i += 1
#         print '%s rows written...' % (i)
#
#     wr.writerow([''])
#     wr.writerow(['Max Load Time : %s - %s' % (the_collector.max_load_time, the_collector.max_load_time_url)])
#     wr.writerow(['Min Load Time : %s - %s' % (the_collector.min_load_time, the_collector.min_load_time_url)])
#     wr.writerow(['Max Requests  : %s - %s' % (the_collector.max_requests, the_collector.max_requests_url)])
#     wr.writerow(['Min Requests  : %s - %s' % (the_collector.min_requests, the_collector.min_requests_url)])
#     wr.writerow(['Max Page Size : %s - %s' % (the_collector.max_page_size, the_collector.max_page_size_url)])
#     wr.writerow(['Min Page Size : %s - %s' % (the_collector.min_page_size, the_collector.min_page_size_url)])
#     wr.writerow([''])
#     wr.writerow(['Average Load Time : %s' % the_collector.get_avg_load_time()])
#     wr.writerow(['Average Requests  : %s' % the_collector.get_avg_requests()])
#     wr.writerow(['Average Page Size : %s' % the_collector.get_avg_page_size()])
#     wr.writerow([''])
#     wr.writerow(['Elapsed Time      : %s' % (time.time() - start)])
#
#
# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print "Please provide input files"
#     else:
#         output_file = sys.argv[1].split('.')[0] + '_output_' + datetime.now().strftime('%d-%m-%y_%H_%M') + '.csv'
#         main(sys.argv[1], output_file)
#         print "Elapsed Time: %s" % (time.time() - start)
#         print "Output File : %s" % output_file
