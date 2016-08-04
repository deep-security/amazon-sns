from __future__ import print_function

# standard library
import datetime
import json
import random
import string
import tempfile

# 3rd party library
import boto3 # pre-installed in AWS Lambda environment

S3_BUCKET_NAME = "deep-security-logs"

def create_s3_key_name(timestamp):
    """
    Create an S3 key name based on the specified timestamp
    """

    # generate a random string to avoid key name conflicts
    # from @mattgemmell at http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
    nonce = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))

    # make sure we have a unique key name, ideally full timestamp + nonce
    key_name = '{}-{}.txt'.format(str(timestamp), nonce)
    if type(timestamp) == type(datetime.datetime.now()):
        key_name = '{}-{}.txt'.format(timestamp.strftime("%Y/%m/%d/%H/%Y-%m-%d-%H-%M-%S-%f"), nonce)

    return key_name

def write_event_to_s3_bucket(event, timestamp, bucket_name):
    """
    Write the Deep Security JSON event to the specified S3 bucket
    """
    result = None

    # get a unique key name based on the event's timestamp
    key_name = create_s3_key_name(timestamp)

    # convert the event to a string for storage
    event_str = None
    try:
        event_str = unicode(json.dumps(event)).encode("utf-8")
    except Exception as err:
        print("Could not convert event to string for storage. Threw exception: {}".format(err))

    if event_str:
        # create a temporary file in order to upload to S3
        tmp_file = tempfile.NamedTemporaryFile(delete=True)
        try:
            tmp_file.write(event_str)
            tmp_file.seek(0) # make sure the temporary file is readable

            s3 = boto3.client('s3')
            s3.upload_file(tmp_file.name, bucket_name, key_name)
            print("Wrote event to S3 as {}".format(key_name))

            result = key_name
        except Exception as err:
            print("Could not write file to S3. Threw exception: {}".format(err))
        finally:
            tmp_file.close() # clean up

    return result

def lambda_handler(event, context):
    """
    Parse the incoming SNS notification for a Deep Security event
    """
    timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    if type(event) == type({}):
        if event.has_key('Records'):
            print("Processing {} records".format(len(event['Records'])))
            for i, record in enumerate(event['Records']):
                print("Record {}/{}".format(i, len(event['Records'])))

                if record.has_key('Sns'):
                    timestamp = datetime.datetime.now()
                    time_received = record['Sns']['Timestamp'] if record['Sns'].has_key('Timestamp') else None
                    if time_received: 
                        try:
                            timestamp = datetime.datetime.strptime(time_received, timestamp_format)
                        except: pass # we can silently fail and try to catch later

                    if record['Sns'].has_key('Message'):
                        record_doc = json.loads(record['Sns']['Message'])

                        if record_doc.has_key('LogDate'):
                            # LogDate is the actually timestamp of the event. We need a timestamp for the
                            # event and the order of preference is:
                            #    1. LogDate
                            #    2. Time received by Amazon SNS
                            #    3. Time processed by AWS Lambda
                            #
                            # When both LogDate and time received by Amazon SNS are present, we'll also
                            # calculate the delivery delay and record that with the event as 'DeliveryDelay'
                            time_generated = record_doc['LogDate']
                            try:
                                tg = datetime.datetime.strptime(time_generated, timestamp_format)
                                timestamp = tg # update the timestamp to the actual event time instead of the time is was received
                                tr = datetime.datetime.strptime(time_received, timestamp_format)
                                d = tr - tg
                                print("Event delivery delay: {}".format(d))
                                record_doc['DeliveryDelay'] = '{}'.format(d)
                            except Exception as err:
                                print(err)

                        save_result = write_event_to_s3_bucket(event=record_doc, timestamp=timestamp, bucket_name=S3_BUCKET_NAME)
                        if save_result:
                            print("Wrote event to S3: {}".format(save_result))
                        else:
                            print("Could not write event to S3")
    else:
        print("Received event: " + json.dumps(event, indent=2))
        
    return True