if (!Date.prototype.toISOString) {
    Date.prototype.toISOString = function () {
        function pad(n) {
            return n < 10 ? '0' + n : n;
        }

        function ms(n) {
            return n < 10 ? '00' + n : n < 100 ? '0' + n : n
        }

        return this.getFullYear() + '-' +
            pad(this.getMonth() + 1) + '-' +
            pad(this.getDate()) + 'T' +
            pad(this.getHours()) + ':' +
            pad(this.getMinutes()) + ':' +
            pad(this.getSeconds()) + '.' +
            ms(this.getMilliseconds()) + 'Z';
    }
}

function createHAR(address, title, startTime, resources) {
    //var entries = [];
    var total_requests = 0;
    var page_size = 0;
    var total_images = 0;
    var total_css = 0;
    var total_js = 0;

    resources.forEach(function (resource) {
        var request = resource.request,
            startReply = resource.startReply,
            endReply = resource.endReply;

        total_requests++;

        if (!request || !startReply || !endReply) {
            return;
        }

        page_size += startReply.bodySize;

        if (endReply.contentType.match(/(image)/)) {
            total_images++;
        }
        if (endReply.contentType.match(/(css)/)) {
            total_css++;
        }
        if (endReply.contentType.match(/(javascript)/)) {
            total_js++;
        }

        // Exclude Data URI from HAR file because
        // they aren't included in specification
        //if (request.url.match(/(^data:image\/.*)/i)) {
        //    return;
        //}

        //entries.push({
        //    startedDateTime: request.time.toISOString(),
        //    time: endReply.time - request.time,
        //    request: {
        //        method: request.method,
        //        url: request.url,
        //        httpVersion: "HTTP/1.1",
        //        cookies: [],
        //        headers: request.headers,
        //        queryString: [],
        //        headersSize: -1,
        //        bodySize: -1
        //    },
        //    response: {
        //        status: endReply.status,
        //        statusText: endReply.statusText,
        //        httpVersion: "HTTP/1.1",
        //        cookies: [],
        //        headers: endReply.headers,
        //        redirectURL: "",
        //        headersSize: -1,
        //        bodySize: startReply.bodySize,
        //        content: {
        //            size: startReply.bodySize,
        //            mimeType: endReply.contentType
        //        }
        //    },
        //    cache: {},
        //    timings: {
        //        blocked: 0,
        //        dns: -1,
        //        connect: -1,
        //        send: 0,
        //        wait: startReply.time - request.time,
        //        receive: endReply.time - startReply.time,
        //        ssl: -1
        //    },
        //    pageref: address
        //});
    });

    return {
        url: address,
        title: title,
        total_requests: total_requests,
        load_time: page.endTime - page.startTime,
        page_size: page_size,
        total_images: total_images,
        total_css: total_css,
        total_js: total_js
        //startDateTime: startTime.toISOString()
        //entries: entries
    };
}

var page = require('webpage').create(),
    system = require('system');

if (system.args.length === 1) {
    console.log('Usage: netsniff.js <some URL>');
    phantom.exit(1);
} else {

    page.address = system.args[1];
    page.resources = [];

    page.onLoadStarted = function () {
        page.startTime = new Date();
    };

    page.onResourceRequested = function (req) {
        page.resources[req.id] = {
            request: req,
            startReply: null,
            endReply: null
        };
    };

    page.onResourceReceived = function (res) {
        if (res.stage === 'start') {
            page.resources[res.id].startReply = res;
        }
        if (res.stage === 'end') {
            page.resources[res.id].endReply = res;
        }
    };

    page.open(page.address, function (status) {
        var har;
        if (status !== 'success') {
            console.log('FAIL to load the address');
            phantom.exit(1);
        } else {
            page.endTime = new Date();
            page.title = page.evaluate(function () {
                return document.title;
            });
            har = createHAR(page.address, page.title, page.startTime, page.resources);
            console.log(JSON.stringify(har, undefined, 4));
            phantom.exit();
        }
    });
}
