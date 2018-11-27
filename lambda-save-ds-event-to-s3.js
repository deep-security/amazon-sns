/*
 * Sample Node.js Lambda script to handle events from Deep Security SNS individually.
 * An example of the S3 file name would be "DeepSecurityEvents/LogInspectionEvent/2018/11/05/9999.json"
 */

// MODIFY THIS HERE FOR YOUR ENVIRONMENT
const bucket = 'YOUR-BUCKET-NAME-HERE';
const acl = 'public-read';
const s3prefix = 'DeepSecurityEvents/';
const ext = '.json';

const aws = require('aws-sdk');
const s3 = new aws.S3();

exports.handler = (sns, context) => {
    //retrieve the events from the sns json
    var events = JSON.parse(sns.Records[0].Sns.Message);

    var receivedDate = getFormattedDate(new Date(sns.Records[0].Sns.Timestamp));

    if(isArray(events)) {
        // From DS 10.0 and onwards, events come as an array. Iterate through it.
        for(var i = 0; i < events.length; i++) {
            sendToS3(events[i], receivedDate);
        }
    } else {
        // Format for DS 9.6 and before, SNS contains a single event
        sendToS3(events, receivedDate);
    }
};

function isArray(obj) {
    return obj.constructor === Array;
}

function getFormattedDate(d) {
    //returns yyyy/MM/dd
    return d.getFullYear() + '/' + twoDigits(d.getMonth() + 1) + '/' + twoDigits(d.getDate());
}

function twoDigits(n) {
    return n < 10 ? '0' + n : n;
}

function sendToS3(event, receivedDate) {
    var params = {
        Bucket: bucket,
        Key: s3prefix + event.EventType + '/' + receivedDate + '/' + event.EventID + ext,
        ACL: acl,
        Body: JSON.stringify(event)
    };
    s3.putObject(params, function(err) {
        if (err) console.log(err, err.stack); // log the error
    });
}