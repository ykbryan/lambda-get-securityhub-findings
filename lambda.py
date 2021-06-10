import json
import boto3
import botocore
import csv

securityhub = boto3.client('securityhub')
s3 = boto3.resource('s3')
_filter = Filters={
    'ComplianceStatus': [
        {
            'Value': 'FAILED',
            'Comparison': 'EQUALS'
        }
    ],
    'RecordState': [
        {
            'Value': 'ACTIVE',
            'Comparison': 'EQUALS'
        }
    ],
    'GeneratorId': [
        {
            'Value': 'aws-foundation',
            'Comparison': 'PREFIX'
        }
    ],
}
_sort = SortCriteria=[
    {
        'Field': 'ComplianceStatus',
        'SortOrder': 'desc'
    },
    {
        'Field': 'SeverityNormalized',
        'SortOrder': 'desc'
    }
]
MAX_ITEMS=100
BUCKET_NAME='yourbucketname'
KEY='securityhubfindings.csv'

def lambda_handler(event, context):
    # cannot seems to pass token = None into the get_findings() 
    result = securityhub.get_findings(
      Filters=_filter,
      SortCriteria=_sort,
      MaxResults=MAX_ITEMS
    )
    
    with open("/tmp/data.csv", "w") as file:
        csv_file = csv.writer(file)
        
        keys = []
        count = 0
        while(result != None): 
            
            items = []
            findings = result['Findings']
            
            for finding in findings: 
                count += 1
                item = {}
                item['standard'] = finding['GeneratorId']
                item['status'] = finding['Compliance']['Status']
                item['severity'] = finding['Severity']['Label']
                item['id'] = finding['ProductFields']['ControlId']
                item['title'] = finding['Title']
                item['account'] = finding['AwsAccountId']
                item['resourceType'] = finding['Resources'][0]['Type']
                item['resourceId'] = finding['Resources'][0]['Id']
                item['json'] = finding
                items.append(item)
                if (len(keys) == 0):
                    keys = list(item.keys())
                    csv_file.writerow(keys)
            
            for d in items:
                csv_file.writerow(list(d.values()))
            
            if "NextToken" in list(result.keys()):
                token = result['NextToken']
                result = securityhub.get_findings(Filters=_filter, SortCriteria=_sort, MaxResults=MAX_ITEMS, NextToken=token)
            else:
                    result = None
    
    csv_binary = open('/tmp/data.csv', 'rb').read()
    
    try:
        obj = s3.Object(BUCKET_NAME, KEY)
        obj.put(Body=csv_binary)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    s3client = boto3.client('s3')
    try:
        download_url = s3client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': KEY
                },
            ExpiresIn=3600
        )
        return {
            "csv_link": download_url,
            "total": count
        }
    except Exception as e:
        raise utils_exception.ErrorResponse(400, e, Log)
    
    return {
        'message': 'Error found, please check your logs',
        'total': 0
    }
