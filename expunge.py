import sys
import pymysql
from datetime import date
from datetime import timedelta
import csv
import json
import passwords
import re
COMPARE_YEAR = 2021
COMPARE_MONTH = 8
COMPARE_DAY = 25

def checkRegistrationCrimes(statute):
    #print("Check Registration Crime",statute)
    statute = statute.strip()
    statute = statute.replace(".", "-")  # Have to do this because the statutes in Joco are seperated by a -
    statute = statute.replace("(", "-")
    statute = statute.replace(")", "-")
    with open('RegistrationCrimes.csv',newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row)
            # We check to see if the first x characters from the given statute match the statute in the csv
            # The reason we do this is some statutes from the db have extra items like 21-5406.OG
            if(statute[0:len(row['Statute'])] == row['Statute']):
                #print("Found a hit",row['Statute'],row['Charge Type'],row['Registration Time Years'],row['Age Requirement'])
                return{"Registration Time Years":row['Registration Time Years'],"Charge Type":row['Charge Type']}
                break
    return None
def checkListJoco(statute,charge_description,charge_type,lvl,offensedate):
    # Check to see if we can find the statute because that takes priority.:

    if(charge_type == None):
        #This was a result of case 10CR02146
        charge_type = ""
    statute = statute.strip()
    charge_description = charge_description.strip()
    charge_type = charge_type.strip()
    with open('statutes.csv',newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row)
            # We check to see if the first x characters from the given statute match the statute in the csv
            # The reason we do this is some statutes from the db have extra items like 21-5406.OG
            if(statute[0:len(row['Statute'])] == row['Statute']):
                #print("Found a hit",row['Statute'],row['Description'],row['Category'])
                return{"Description":row['Description'],"Category":row['Category']}
                break

    #Check if Tabacco Infraction
    if('TOBACCO' in charge_description.upper()):
        return {"Description": "Tobacco", "Category": "3 Year"}
    # Check for DUI
    elif(statute[0:6] == '8-1567'):
        # Need to check what DUI this is. First second third etc
        # This is done by looking at the number after the period 8-1567.2 means second DUI
        if(len(statute) == 6):
            # No .number after the statute
            #If no number we treat it as the first DUI
            return {"Description": "DUI", "Category": "5 Year"}
        elif('.' in statute):
            num_times = statute.split('.')[1]
            if(num_times == 'CR'):
                # Treat it as a first DUI
                return False
            elif(num_times == '1'):
                return {"Description": "DUI", "Category": "5 Year"}
            elif(num_times in ('2','3','4','3M')):
                if (offensedate == None):
                    # We need the offense date for DUI cases.
                    return False
                # More than first DUI
                #We need to check if the offense date was between July 1st, 2014 and June 30th 2015 as those fall into a special 7 year category
                #The expungement statute in effect for that year allowed for expungement of all DUIs at 7 years.
                #Now it's 5 for a first and 10 for a second and defendant get's the better of the statutes.
                if (offensedate < date(2006, 7, 1)):
                    #All DUIs get five years if before this date.
                    return {"Description": "DUI", "Category": "5 Year"}
                elif(offensedate >= date(2014, 7, 1) and offensedate < date(2015, 7, 1)):
                    #This is the only 7 year category
                    return {"Description": "DUI", "Category": "7 Year"}
                else:
                    return {"Description": "DUI", "Category": "10 Year"}
            else:
                return False
    # Check for Prostitution
    elif ('PROSTITUTION' in charge_description.upper()):
        return {"Description": "Prostitution", "Category": "1 Year"}
    # Check for Misdemanors
    elif(charge_type == 'M'):
        return {"Description": "Misdemeanor", "Category": "3 Year"}
    # Check for Infractions
    # Andrew is looking at whether just looking I is good enough. I think it is because almost all the I tp in the database are traffic cases.
    elif(charge_type == 'I'):
        return {"Description": "Traffic Infraction", "Category": "3 Year"}
    #Check for drug crimes
    elif(lvl != None and len(lvl) == 2 and lvl[1] == 'D'):
        if (offensedate == None):
            # We need the offense date for drug cases.
            return False
        #This is almost all AD. There is only one BD and none of the others.
        if(lvl[0] in ('A','B','C')):
            # 5 years
            return {"Description": "Drug ABC", "Category": "5 Year"}
        elif(lvl[0] in ('D','E')):
            # 3 Years
            return {"Description": "Drug DE", "Category": "3 Year"}
        elif(lvl[0] in ('1','2','3','4','5')):
            if (offensedate >=  date(1993, 7, 1) and offensedate <=  date(2012, 7, 1)):
                # Drug level 4 is allowed
                # There was no level 5 prior to 2012
                if (lvl[0] == '4'):
                    return {"Description": "Drug 4", "Category": "3 Year"}
                elif(lvl[0] in ('1','2','3')):
                    return {"Description": "Drug 123", "Category": "5 Year"}
                else:
                    #Could be 5
                    return False
            elif (offensedate >  date(2012, 7, 1)):
                # They created a level 5 drug category and made that 3 year while moving a 4 level drug category to the 5 year wait period.
                if (lvl[0] in ('1','2','3','4')):
                    return {"Description": "Drug 1234", "Category": "5 Year"}
                elif (lvl[0] == '5'):
                    return {"Description": "Drug 5", "Category": "3 Year"}
            else:
                return False
        elif(lvl[0] in ('1','2','3')):
            #5 years
            return {"Description": "Drug 123", "Category": "5 Year"}
        elif(lvl[0] in ('4','5')):
            #3 Years
            return {"Description": "Drug 45", "Category": "3 Year"}
        else:
            return False
    #Check non drug crimes
    elif(lvl != None and lvl.isnumeric() == True):
        temp_lvl = int(lvl)
        if(temp_lvl <= 5):
            return {"Description": "Non Drug 12345", "Category": "5 Year"}
        elif(temp_lvl >= 6 and temp_lvl <= 10):
            return {"Description": "Non Drug 678910", "Category": "3 Year"}
        else:
            #There should be anything bigger than 10 but just in case.
            return False
    else:
        return False #Means nothing was found.

def checkListState(statute,charge_description,lvl,offensedate):
    # Check to see if we can find the statute because that takes priority.:

    statute = statute.strip()
    statute = statute.replace(".", "-")  # Have to do this because the statutes in Joco are seperated by a -

    with open('statutes.csv',newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row)
            # We check to see if the first x characters from the given statute match the statute in the csv
            # The reason we do this is some statutes from the db have extra items like 21-5406.OG
            if(statute[0:len(row['Statute'])] == row['Statute']):
                #print("Found a hit",row['Statute'],row['Description'],row['Category'])
                return{"Description":row['Description'],"Category":row['Category']}
                break

    #Check if Tabacco Infraction
    if('TOBACCO' in charge_description.upper()):
        return {"Description": "Tobacco", "Category": "3 Year"}
    # Check for DUI
    elif(statute[0:6] == '8-1567'):
        # Need to check what DUI this is. First second third etc
        # For state wide the nth conviction is in the description NOT the statute like in Joco
        if(charge_description == "Driving under influence of alcohol or drugs; Misdemeanor"):
            #We treat as a first conviction
            return {"Description": "DUI", "Category": "5 Year"}
        elif("1st" in charge_description):
            #Means first DUI
            return {"Description": "DUI", "Category": "5 Year"}
        elif("2nd" in charge_description or '3rd' in charge_description or '4th' in charge_description):
            #More than one DUI
            if (offensedate < date(2006, 7, 1)):
                # All DUIs get five years if before this date.
                return {"Description": "DUI", "Category": "5 Year"}
            elif (offensedate >= date(2014, 7, 1) and offensedate < date(2015, 7, 1)):
                # This is the only 7 year category
                return {"Description": "DUI", "Category": "7 Year"}
            else:
                return {"Description": "DUI", "Category": "10 Year"}
        else:
            #Unknown
            return False
    # Check for Prostitution
    elif ('PROSTITUTION' in charge_description.upper()):
        return {"Description": "Prostitution", "Category": "1 Year"}
    # Check for Misdemanors
    elif('misdemeanor' in lvl.lower()):
        return {"Description": "Misdemeanor", "Category": "3 Year"}
    # Check for Infractions
    elif(lvl == 'Infraction'):
        return {"Description": "Traffic Infraction", "Category": "3 Year"}
    #Check for drug crimes
    if('Drug' in lvl):
        if(offensedate >= date(1993, 7, 1) and offensedate <= date(2012, 7, 1)):
            #Drug level 4 is allowed
            #There was no level 5 prior to 2012
            if ('4' in lvl):
                return {"Description": "Drug 4", "Category": "3 Year"}
            else:
                return {"Description": "Drug 123", "Category": "5 Year"}
        elif(offensedate >date(2012, 7, 1)):
            #They created a level 5 drug category and made that 3 year while moving a 4 level drug category to the 5 year wait period.
            if('1' in lvl or '2' in lvl or '3' in lvl or '4' in lvl):
                return {"Description": "Drug 1234", "Category": "5 Year"}
            elif('5' in lvl):
                return {"Description": "Drug 5", "Category": "3 Year"}
        else:
            return False
    #Check non drug crimes
    elif("Felony" in lvl and re.search('\d',lvl)):
        number = re.findall('\d+',lvl)[0]

        if(int(number) <= 5):
            return {"Description": "Non Drug 12345", "Category": "5 Year"}
        elif(int(number) >= 6 and int(number) <= 10):
            return {"Description": "Non Drug 678910", "Category": "3 Year"}
        else:
            #There shouldn't be anything bigger than 10 but just in case.
            return False
    elif(lvl == 'Felony Non-Grid'):
        return {"Description": "Non-Grid Felony", "Category": "3 Year"}
    elif(lvl == 'Felony Off Grid'):
        return {"Description": "Felony Off Grid", "Category": "5 Year"}
    else:
        return False #Means nothing was found.
def calculateDays(sentence):
    # This function takes a statement like 1 year, 3 months, 180 days and turns it into the raw days.
    # This way the final_jail_time and probation time can be compared. We just go with the highest one to be safe
    total_time = 0
    if(sentence == None):
        return 0
    if(sentence == '6.5 months'):
        # There is one case with this format 14CR02218
        sentence = "6 months, 15 days"
    # This will return an array with only 1 item if there are no commas so no need to check
    sent_array = sentence.split(',')
    for piece in sent_array:
        if('year' in piece):
            total_time += int(piece.strip().split(' ')[0]) * 365
        elif('month' in piece):
            total_time += int(piece.strip().split(' ')[0]) * 30
        elif('day' in piece):
            total_time += int(piece.strip().split(' ')[0])
        else:
            print("Error in calculating days.")
            sys.exit(0) #Replace with throwing an error
    return total_time


def checkWaitTime(crime_cat,sentenced_date,final_jail_time,probation):
    # This function returns True if enough time has passed or the date on which enough time will have passed.
    # Combine jail time and probation time. Then add the wait time on to that. I'm not entirely sure if this is accurate as there might have been time served that shouldn't then count but there
    # is no indicator of this.
    # This should work if both are zero or empty
    #print(sentenced_date)
    if(sentenced_date == None or sentenced_date == '0000-00-00'):
        #Implemented for 15CR00816
        return None
    special_sentences = {'LIFE NO PAROLE':'99 years',
                         'LIFE MIN 50YR':'50 years',
                         'LIFE MIN 40YR':'40 years',
                         'LIFE MIN 25YR':'25 years',
                         'LIFE MIN 20YR':'20 years',
                         'LIFE MIN 15YR':'15 years',
                         'DEATH SENT':'99 years'}

    if(final_jail_time in special_sentences):
        final_jail_time = special_sentences[final_jail_time]

    jailtimedays = calculateDays(final_jail_time)
    probationtimedays = calculateDays(probation)
    greatest_time = jailtimedays + probationtimedays

    # Take the sentence date plus the greatest number days
    # clock start date is the date when the 3 or 5 years starts ticking.
    #print(sentenced_date)
    clock_start_date = sentenced_date + timedelta(days=greatest_time)
    if(crime_cat == '1 Year'):
        days = 365
    elif(crime_cat == '3 Year'):
        days = 1095
    elif(crime_cat == '5 Year'):
        days = 1825
    elif(crime_cat == '7 Year'):
        days = 2555
    elif(crime_cat == '10 Year'):
        days = 3650
    elif (crime_cat == '15 Year'):
        days = 5475
    elif (crime_cat == '25 Year'):
        days = 9125
    elif(crime_cat == 'Life'):
        days = 36500
    else:
        return None

    # Check if the sentence date plus either 5 or 3 years is less than today.
    # If it is return True if it is not return the date on which it will become eligible.
    today = date(COMPARE_YEAR, COMPARE_MONTH, COMPARE_DAY)
    if(clock_start_date + timedelta(days=days) < today):
        return None
    else:
        daysremaining = (clock_start_date + timedelta(days=days) - today).days
        return today + timedelta(days=daysremaining)
def pullRecordJoco(firstname,lastname,dob, connection):
    cursor = connection.cursor()
    if(dob is None or dob == ""):
        #12CR01447 has no dob
        sql = "SELECT * FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER JOIN sentence ON caseinfo.casenumber = sentence.casenumber" \
          " WHERE def_fname='" + firstname + "' and def_lname ='" + lastname + "'"
        cursor.execute(sql)
    else:
        # if(type(dob) is date):
        #     dobsql =
        sql = "SELECT * FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER JOIN sentence ON caseinfo.casenumber = sentence.casenumber" \
          " WHERE def_fname='" + firstname + "' and def_lname ='" + lastname + "' and dob= %s"
        cursor.execute(sql, (dob,))
    #print(sql)



    results = cursor.fetchall()
    return results
def searchForRegistrationCrimeInRecordJoco(cases):
    registration_wait_time = None
    for result in cases:
        if(result['finding'] != None and result['finding'][0:6].upper() == 'GUILTY'):
            registry_result = checkRegistrationCrimes(result['section'])

            if(registry_result != None):
                # if(registry_result['Registration Time Years'] == 'Life'):
                #     return date(2100, 1, 1)
                temp_registration_wait_time = checkWaitTime(registry_result['Registration Time Years'], result['sentdate'],result['finjail'], result['oriprob'])

                if(temp_registration_wait_time != None and (registration_wait_time ==  None or temp_registration_wait_time > registration_wait_time)):
                    #Someone could have more than one crime that requires registration. We pick the one with the longest wait time.
                    registration_wait_time = temp_registration_wait_time

    return registration_wait_time
def searchForFelonyJoco(cases):
    today = date(COMPARE_YEAR, COMPARE_MONTH, COMPARE_DAY)
    twoyearsago = today - timedelta(days=730)
    return_array = {
        'Active_Felony':False,
        'Case_within_two_years':False,
        'Cases':[]
    }
    for result in cases:
        #print(result)
        #Check for active felony.
        if(result['tp'] == None):
            #We can't ascertain if it's a felony or not so we just ignore it.
            #i.e. if no TP is listed we assume it's a misdemeanor
            #TODO: This might be problematic for fugative cases
            print("TP Not Present",result['casenumber'])
        elif(result['tp'].upper() == 'F' and result['finding'] == None):
            # Felony found
            # This is probably over inclusive of finding active felonies. I think if someone had a felony that was amended to a M and the case was active it wouldn't count as an "active felony"
            # under the law but here it would count as an active felony.
            # Now we need to check if there is a sentence given in the case to make sure it's not a case where the charge was amended. (15CR00005)
            if(result['finjail'] == None and result['oriprob'] == None):
            #     #Checks to see if either the final jail time or probation time is None.
                return_array['Cases'].append({"CaseNumber":result['casenumber'],"Reason":"Active Felony"})
                return_array['Active_Felony'] = True
                #print("Active felony found")
            # else:
            #     print("This is a case where the charge was amended")
        elif(result['tp'].upper() == 'F' and result['finding'][0:6].upper() == 'GUILTY'):
            #We now have to check the sent date/regular date because of rare cases like 19CR01063 which is a guilty without a sent date.
            #We essentially just make the date column the sent date if it doesn't exist.
            # Felony Conviction Within 2 years
            if((result['sentdate'] != None and result['sentdate'] > twoyearsago) or (result['sentdate'] == None and result['date'] != None and result['date'] > twoyearsago)):
                return_array['Cases'].append({"CaseNumber": result['casenumber'], "Reason": "Felony Conviction Within 2 Years"})
                return_array['Case_within_two_years'] = True
    # print(return_array)
    return return_array
def searchForRegistrationCrimeInRecordState(firstname,lastname,dob, connection):
    registration_wait_time = None
    sql = "SELECT kp.`Case ID` FROM kansas2022.parties as kp INNER JOIN kansas2022.case_information as kci ON kp.`Case ID` = kci.`Case ID` WHERE `Party Type` = 'Defendant' AND `Party Name` LIKE %s AND `DOB` = %s"
    cursor = connection.cursor()
    name = lastname +", " + firstname + "%"
    #print(name,dob)
    cursor.execute(sql,(name,dob))
    results = cursor.fetchall()
    if (cursor.rowcount == 0):
        return None
    cursor = connection.cursor()
    cursor.execute(sql, (lastname + ", " + firstname + "%", dob))
    results = cursor.fetchall()
    for result in results:
        #print(result)
        sql2 = '''
        SELECT * FROM kansas2022.charge_information as ci INNER JOIN kansas2022.disposition_events as de ON ci.`Case ID` = de.`Case ID` and ci.`Case ID` = %s  and  `Event Type` = ' Disposition' and (Disposition LIKE '%%Guilty%%' AND Disposition NOT LIKE '%%Not%%') GROUP BY ci.`Case ID`,de.`Charge No`
        '''
        cursor2 = connection.cursor()
        cursor2.execute(sql2, (result['Case ID']))
        results2 = cursor2.fetchall()
        for charge in results2:
            print(charge)
            registry_result = checkRegistrationCrimes(charge['Statute'])

            if (registry_result != None):
                # if (registry_result['Registration Time Years'] == 'Life'):
                #     return date(2100, 1, 1)
                temp_registration_wait_time = checkWaitTime(registry_result['Registration Time Years'],charge['Date'],None,None)
                if(temp_registration_wait_time != None and (registration_wait_time ==  None or temp_registration_wait_time > registration_wait_time)):
                    # Someone could have more than one crime that requires registration. We pick the one with the longest wait time.
                    registration_wait_time = temp_registration_wait_time
    return registration_wait_time
def searchForFelonyState(firstname,lastname,dob, connection):
    #Check for active felonies first
    sql = "SELECT kp.`Case ID` FROM kansas2022.parties as kp INNER JOIN kansas2022.case_information as kci ON kp.`Case ID` = kci.`Case ID` WHERE `Party Type` = 'Defendant' AND `Party Name` LIKE %s AND `Case Status` LIKE 'Pending%%' AND `Case Type` LIKE 'CR Felony%%' AND `DOB` = %s"
    #print(sql)
    return_array = {
        'Active_Felony':False,
        'Case_within_two_years':False,
        'Cases':[]
    }
    cursor = connection.cursor()
    name = lastname +", " + firstname + "%"
    #print(name,dob)
    cursor.execute(sql,(name,dob))
    results = cursor.fetchall()
    #print("Row Count 1:",cursor.rowcount)
    #print(results)
    if(cursor.rowcount != 0):
        return_array['Active_Felony'] = True

    #Check for past felonies second
    sql = '''SELECT * FROM kansas2022.parties as kp 
    INNER JOIN
    kansas2022.charge_information as kci ON kp.`Case ID` = kci.`Case ID` 
    WHERE `Party Type` = 'Defendant' AND `Party Name` LIKE %s
    AND `DOB` = %s AND Level LIKE 'Felony%%'
    '''
    cursor = connection.cursor()
    cursor.execute(sql,(lastname +", " + firstname + "%",dob))
    results = cursor.fetchall()
    twoyearsago = '2019-08-25'
    for result in results:
        sql2 = '''
        SELECT * FROM kansas2022.disposition_events WHERE `Case ID` = %s AND  `Charge No` = %s and `Event Type` = ' Disposition' and (Disposition LIKE '%%Guilty%%' AND Disposition NOT LIKE '%%Not%%') AND 
        Date > %s
        '''
        cursor2 = connection.cursor()
        cursor2.execute(sql2, (result['Case ID'],result['Charge No'],twoyearsago))
        results2 = cursor2.fetchall()
        if (cursor2.rowcount != 0):
            return_array['Case_within_two_years'] = True
    return return_array

def createExpungementCSV(cases):
    with open("expungement_cases.csv",'w',newline='') as csvfile:
        for temp in cases:
            fieldnames = list(cases[temp][0].keys())
            fieldnames.append("Case Number")
            break
        writer = csv. DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            for charge in cases[case]:
                temp = charge
                temp['Case Number'] = case
                writer.writerow(temp)

def pullStateCases(limit,connection,year,singlecase = None):
    finalarray = []
    if(singlecase == None):
        sql = '''
        SELECT chargei.`Case ID` as casenumber,Description as title,Level as lvl,Statute as statute,`Charge No` as charge_id,Court,OffenseDate FROM kansas2022.charge_information as chargei
        INNER JOIN kansas2022.case_information as casei on casei.`Case ID` = chargei.`Case ID` WHERE `File Date` >= '1993-07-01' LIMIT %s
        '''
    else:
        sql = '''
        SELECT chargei.`Case ID` as casenumber,Description as title,Level as lvl,Statute as statute,`Charge No` as charge_id,Court,OffenseDate FROM kansas2022.charge_information as chargei
        INNER JOIN kansas2022.case_information as casei on casei.`Case ID` = chargei.`Case ID` and `File Date` >= '1993-07-01' AND casei.`Case ID` = "''' + singlecase + '''"LIMIT %s
        '''
    # sql = '''
    # SELECT chargei.`Case ID` as casenumber,Description as title,Level as lvl,Statute as statute,`Charge No` as charge_id,Court,OffenseDate FROM kansas.charge_information as chargei
    # INNER JOIN kansas.case_information as casei on casei.`Case ID` = chargei.`Case ID`
    # WHERE chargei.`Case ID` = '1197713' LIMIT %s
    # '''
    cursor = connection.cursor()
    #cursor.execute(sql,('20'+year,limit))
    cursor.execute(sql,(limit,))

    results = cursor.fetchall()
    # Cycle through all the charges
    for result in results:
        sql2 = "SELECT * from kansas2022.disposition_events WHERE `Case ID` = %s and `Charge No` = %s and  `Event Type` = ' Disposition' ORDER BY ID DESC LIMIT 1"
        cursor.execute(sql2,(result['casenumber'],result['charge_id']))
        results2 = cursor.fetchall()
        #print(sql2,result['casenumber'],result['charge_id'],results2)
        if(results2 != () and ('Guilty' in results2[0]['Disposition'] and 'Not' not in results2[0]['Disposition'])):
            sql3 = "SELECT * FROM kansas2022.parties WHERE `Case ID` = %s and `Party Type` = 'Defendant' LIMIT 1"
            cursor.execute(sql3, (result['casenumber'],))
            results3 = cursor.fetchall()
            if(results3 != ()):
                # print(results3)
                # print(results3[0])
                if(',' in results3[0]['Party Name']):
                    fname = results3[0]['Party Name'].split(',')[1].strip()
                    lname = results3[0]['Party Name'].split(',')[0].strip()
                else:
                    fname = results3[0]['Party Name'].strip()
                    lname = ""
                result.update({
                    'def_fname' :fname,
                    'def_lname': lname,
                    'dob':results3[0]['DOB'],
                    'finjail' : None,
                    'oriprob' : None,
                    'sentdate' : results2[0]['Date']
                })
                finalarray.append(result)
    #print(finalarray)
    return finalarray

def pullJocoCases(limit,connection,year,singlecase=None):
    if (singlecase == None):
        # sql = "SELECT *,charges.id as charge_id, 'Johnson County' as Court FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER " \
        #       "JOIN sentence ON sentence.casenumber = charges.casenumber WHERE caseinfo.casenumber LIKE '%" + year + "CR%' AND SUBSTRING(finding,1,6) = 'GUILTY'" \
        #       "LIMIT " + str(limit)
        sql = "SELECT *,charges.id as charge_id, 'Johnson County' as Court,date as OffenseDate FROM joco2022.caseinfo INNER JOIN joco2022.charges ON caseinfo.casenumber = charges.casenumber INNER " \
              "JOIN joco2022.sentence ON sentence.casenumber = charges.casenumber WHERE caseinfo.casenumber LIKE '%CR%' AND SUBSTRING(finding,1,6) = 'GUILTY' and charges.sentdate >= '1993-07-01' AND charges.sentdate IS NOT NULL " \
              "LIMIT " + str(limit)
    else:
        sql = "SELECT *,charges.id as charge_id, 'Johnson County' as Court, date as OffenseDate FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER " \
              "JOIN sentence ON sentence.casenumber = charges.casenumber WHERE caseinfo.casenumber = '" + singlecase + "' and SUBSTRING(finding,1,6) = 'GUILTY' AND charges.sentdate >= '1993-07-01' and charges.sentdate IS NOT NULL"
    print(sql)
    cursor = connection.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    return results
def search2(limit,connection,year,county,singlecase=None):
    if(county == 'Joco'):
        results = pullJocoCases(limit,connection,year,singlecase)
    else:
        #Means it's a state charge
        results = pullStateCases(limit,connection,year,singlecase)


    # Cycle through all the charges
    priorresult = False

    for result in results:
        #print(result)
        final = analysis(result,county,priorresult)
        print(final)
        saveSQL(final,connection)
        priorresult = result

def getJocoOffenseDateForAmendedCharge(chargeid):
    sql = "SELECT date as OffenseDate FROM joco2022.charges WHERE id=" + str(chargeid - 1)
    cursor = connection.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    return results[0]['OffenseDate']
def analysis(charge,county,priorresult):
    print(charge['casenumber'])
    if(charge['def_fname'] == None):
        charge['def_fname'] = ""
    if(charge['def_lname'] == None):
        charge['def_lname'] = ""
    outcome = 'Error'
    expungement_category = "Error"
    crime_description = "Error"
    felony_last_two = False
    active_felony = False
    waittime_result = None
    registration_wait_time = None
    registration_category = None
    registration_charge_type = None

    # 1 check if we recognize the statute or charge type
    registration_crime = None
    registry_current_case = False
    if(county == 'Joco'):
        if(charge['chargecount'] == 'Amended'):
            #Pull the date from
            #Some amended charges don't have offense dates.
            charge['OffenseDate'] = getJocoOffenseDateForAmendedCharge(charge['charge_id'])
        registration_crime = checkRegistrationCrimes(charge['section'])
        check_charge = checkListJoco(charge['section'], charge['title'], charge['tp'], charge['lvl'],charge['OffenseDate'])
    if(county == 'State'):
        registration_crime = checkRegistrationCrimes(charge['statute'])
        check_charge = checkListState(charge['statute'], charge['title'], charge['lvl'],charge['OffenseDate'])
    #print(check_charge)
    if (check_charge == False):
        description = 'Unknown Crime Category'
        expungement_category = "Unknown Crime Category"
    else:
        crime_description = check_charge['Description']
        expungement_category = check_charge['Category']

    # 2 Check the wait time
    if (expungement_category == '1 Year' or expungement_category == '5 Year' or expungement_category == '3 Year' or expungement_category == '7 Year' or expungement_category == '10 Year'):
        waittime_result = checkWaitTime(expungement_category, charge['sentdate'], charge['finjail'],charge['oriprob'])

    #2.5 Check registration wait time
    if(registration_crime != None):
        registry_current_case = True
        registration_charge_type = registration_crime['Charge Type']

        registration_wait_time = checkWaitTime(registration_crime['Registration Time Years'], charge['sentdate'], charge['finjail'],charge['oriprob'])
    # 3 Check if there is an active felony  # 4 Check if there is a felony conviction within 2 years.
    if(county == 'Joco'):
        record = pullRecordJoco(charge['def_fname'], charge['def_lname'], charge['dob'], connection)
        felony_result = searchForFelonyJoco(record)
        registration_crime = searchForRegistrationCrimeInRecordJoco(record)
    else:
        felony_result = searchForFelonyState(charge['def_fname'], charge['def_lname'], charge['dob'], connection)
        registration_crime = searchForRegistrationCrimeInRecordState(charge['def_fname'], charge['def_lname'], charge['dob'], connection)
    if (felony_result['Active_Felony'] == True):
        active_felony = True
    if (felony_result['Case_within_two_years'] == True):
        felony_last_two = True
    # Check Outcome
    if(expungement_category == "Unknown Crime Category" or expungement_category == 'Ineligible'):
        outcome = expungement_category
    elif(felony_last_two == True or active_felony == True or type(waittime_result) is date or type(registration_wait_time) is date):
        outcome = "Not Yet Eligible"
    else:
        outcome = "Eligible"
    #print(outcome)
    if(county == 'Joco'):
        if (charge['dob'] == None):
            person = charge['def_fname'] + "@@@" + charge['def_lname'] + "@@@Unknown"
        else:
            person = charge['def_fname'] + "@@@" + charge['def_lname'] + "@@@" + charge['dob'].strftime("%m/%d/%Y")
    else:
        if(charge['dob'] == None):
            person = charge['def_fname'] + "@@@" + charge['def_lname'] + "@@@" + "Unknown"
        else:
            person = charge['def_fname'] + "@@@" + charge['def_lname'] + "@@@" + charge['dob']


    final = {
        "Case Number":charge['casenumber'],
        "Charge ID":charge['charge_id'],
        "Person":person,
        "Charge":charge['title'],
        "Expungement Category":expungement_category,
        "Crime Description":crime_description,
        "Date Eligible":waittime_result,
        "Registry Wait Time": registration_wait_time,
        "Registry Category": registration_charge_type,
        "Registry Current Case":registry_current_case,
        "Registry in Record":registration_crime,
        "Felony Conviction":felony_last_two,
        "Active Felony":active_felony,
        "Outcome":outcome,
        "County":charge['Court']
    }
    return final
def saveSQL(item,connection):
    # Create a new record
    cursor = connection.cursor()
    sql = "INSERT INTO kansas_expungement2022.analysis2022 (CaseNumber,ChargeID,Person,Charge,ChargeCategory,ExpungementCategory,WaitTime,RegistryWaitTime,RegistryCategory,RegistryCurrentCase,RegistryInRecord,FelonyConvictionLastTwoYears,FelonyPending,Outcome,County)" \
          " VALUES (%s, %s,%s, %s,%s, %s,%s, %s,%s,%s,%s,%s,%s,%s,%s)"
    #print(list(item.values()))
    cursor.execute(sql,list(item.values()))

    # connection is not autocommit by default. So you must commit to save
    # your changes.
    connection.commit()

def search(limit,connection,year,singlecase = None):
    # Query to pull cases from the database.
    # There query pulls a list of charges not of cases.
    # It also only pulls charges where the conviction was a guilty since we are only concerned with expunging convictions.
    # It temporarly only pulls cases from 2015 for testing.
    if(singlecase == None):
        sql = "SELECT *,charges.id as charge_id FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER " \
              "JOIN sentence ON sentence.casenumber = charges.casenumber WHERE caseinfo.casenumber LIKE '%" + year + "CR%' AND SUBSTRING(finding,1,6) = 'GUILTY'" \
              "LIMIT " + str(limit)
    else:
        sql = "SELECT *,charges.id as charge_id FROM caseinfo INNER JOIN charges ON caseinfo.casenumber = charges.casenumber INNER " \
              "JOIN sentence ON sentence.casenumber = charges.casenumber WHERE caseinfo.casenumber = '" + singlecase + "' and SUBSTRING(finding,1,6) = 'GUILTY'"
    cursor = connection.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    cases = {}
    #Cycle through all the charges
    for result in results:
        # 1 check if we recognize the statute or charge type
        # 2 Check the wait time
        # 3 Check if there is an active felony
        # 4 Check if there is a felony conviction within 2 years.
        #print(result)
        casenumber = result['casenumber']
        if(casenumber not in cases):
            cases[casenumber] = []
        # Check Charge
        # This will check to see if the charge falls into a recognizable charge category. Either a misdemeanor or a specifically mentioned statute.
        check_charge = checkListJoco(result['section'],result['title'],result['tp'],result['lvl'])
        if(check_charge == False):
            # Charge Not Recognized so end the analysis and return the outcome as "Unknown Crime Category"
            cases[casenumber].append({'ChargeNo':result['charge_id'],'Outcome':'Unknown Crime Category','Wait Time Result':"Wait Time Not Run",'Active Felony':'Not Searched','Case_within_two_years':'Not Searched'})
        elif(check_charge['Category'] == 'Ineligible'):
            # Charge not eligible.
            # This means we were able to identify the charge description but it is for a charge that is ineligible (i.e. Murder 1st Degree). End the anlaysis and return "Ineligible"
            cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Ineligible','Wait Time Result':'Wait Time Not Run','Active Felony':'Not Searched','Case_within_two_years':'Not Searched'})
        elif(check_charge['Category'] == '1 Year' or check_charge['Category'] == '5 Year' or check_charge['Category'] == '3 Year' or check_charge['Category'] == '7 Year' or check_charge['Category'] == '10 Year'):
            # Check if the waiting time has progressed long enough.
            # This means we recognized the charge description/statute and the category is initially eligible like a misdemeanor.
            # Now we check to see if enough time has passed. Either 3 or 5 years from the end of the sentence.
            # The checkWaitTime function returns a True if enough time has passed, the date it becomes eligible if not enough time has passed, or a None if we hit an error.
            waittime_result = checkWaitTime(check_charge['Category'], result['sentdate'], result['finjail'], result['oriprob'])
            if(waittime_result != None):
                # Check Felony Record
                # Wait time could be either good or bad.
                felony_result = searchForFelonyJoco(result['def_fname'],result['def_lname'],result['dob'],connection)
                if(felony_result['Active_Felony'] == True):
                    cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Active Felony','Wait Time Result':waittime_result,'Active Felony':felony_result['Active_Felony'],'Case_within_two_years':felony_result['Case_within_two_years'],'Problem Case Numbers':json.dumps(felony_result['Cases'])})
                elif(felony_result['Case_within_two_years'] == True):
                    cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Felony Within 2 years','Wait Time Result':waittime_result,'Active Felony':felony_result['Active_Felony'],'Case_within_two_years':felony_result['Case_within_two_years'],'Problem Case Numbers':json.dumps(felony_result['Cases'])})
                elif(waittime_result == True):
                    # Means it's eligible and enough time has passed
                    cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Eligible','Wait Time Result':waittime_result,'Active Felony':felony_result['Active_Felony'],'Case_within_two_years':felony_result['Case_within_two_years']})
                elif(type(waittime_result) is date):
                    # Means it's eligible just not enough time has passed
                    cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Not Yet Eligible','Wait Time Result':waittime_result,'Active Felony':felony_result['Active_Felony'],'Case_within_two_years':felony_result['Case_within_two_years']})
                else:
                    # Shouldn't reach this part
                    cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Unknown','Wait Time Result':waittime_result,'Active Felony':felony_result['Active_Felony'],'Case_within_two_years':felony_result['Case_within_two_years']})
            else:
                #Means the wrong crime was sent somehow
                cases[casenumber].append({'ChargeNo': result['charge_id'], 'Outcome': 'Incorrect Waittime Category','Wait Time Result':waittime_result,'Active Felony':'Not Searched','Case_within_two_years':'Not Searched'})
        else:
            cases[casenumber].append({'ChargeNo':result['charge_id'],'Outcome':check_charge['Category'],'Wait Time Result':waittime_result,'Active Felony':'Not Searched','Case_within_two_years':'Not Searched'})

        #Add the problem cases key to the dictionary if it doesn't exist
        if('Problem Case Numbers' not in cases[casenumber][-1]):
            cases[casenumber][-1]['Problem Case Numbers'] = False
        cases[casenumber][-1]['Statute'] = result['section']
        cases[casenumber][-1]['Crime'] = result['title']
        cases[casenumber][-1]['Disposition'] = result['finding']
        cases[casenumber][-1]['Charge Level'] = result['tp']
        cases[casenumber][-1]['Disposition Date'] = result['sentdate']
        cases[casenumber][-1]['Def First Name'] = result['def_fname']
        cases[casenumber][-1]['Def Middle Name'] = result['def_mname']
        cases[casenumber][-1]['Def Last Name'] = result['def_lname']
        cases[casenumber][-1]['Def DOB'] = result['dob']
        cases[casenumber][-1]['Def Race'] = result['race']
        cases[casenumber][-1]['Def Sex'] = result['sex']
    return cases
#statute='21-5406'
#print(checkList(statute))
# print(calculateDays('5 years'))
# print(date.today())
# print(checkWaitTime('3 Years',date(2016,4,23),'1 years, 1 month','8 months, 2 days'))
if __name__ == '__main__':
    ip = passwords.ip
    user = passwords.user
    password = passwords.password
    db = passwords.db

    print(ip)
    connection = pymysql.connect(
        host=ip,
        user=user,
        password=password,
        db=db,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor)

    #search2(3000000,connection,"15",'Joco')
    #search2(20,connection,"20",'Joco',singlecase= '18CR00960')
    search2(3000000,connection,"12","State")
    #cases = search(15000,connection,'17')

    #print(cases)
