from flask import Flask, escape, request
from flask_cors import CORS
import pickle
import random
import numpy as np
import ast
import os
from flask_pymongo import PyMongo
from bson.binary import Binary

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/timetable"
mongo = PyMongo(app)
cors = CORS(app)
print(mongo)


class Course:
    def __init__(self, id, name, no_of_hours, no_of_valid_rooms, valid_rooms, max_no_hours_per_day, max_consecutive_hours, no_of_hours_to_schedule_when_assigning, day_count_dict, class_flag, batch_flag):
        self.id = id
        self.name = name
        self.no_of_hours = no_of_hours
        self.no_of_valid_rooms = no_of_valid_rooms
        self.valid_rooms = valid_rooms
        self.max_no_hours_per_day = max_no_hours_per_day
        self.max_consecutive_hours = max_consecutive_hours
        self.no_of_hours_to_schedule_when_assigning = no_of_hours_to_schedule_when_assigning
        self.day_count_dict = day_count_dict
        self.class_flag = class_flag
        self.batch_flag = batch_flag


class Student_Group:
    def __init__(self, id, name, courses):
        self.id = id
        self.name = name
        self.courses = courses


class Lecturer:
    def __init__(self, id, name, department, max_no_hours_per_day, max_no_hours_per_week, max_consecutive_hours, rank, availability, courses, day_count_dict):
        self.id = id
        self.name = name
        self.department = department
        self.max_no_hours_per_day = max_no_hours_per_day
        self.max_no_hours_per_week = max_no_hours_per_week
        self.max_consecutive_hours = max_consecutive_hours
        self.rank = rank
        self.availability = availability
        self.courses = courses
        self.day_count_dict = day_count_dict


class Room:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class Day:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class Hour:
    def __init__(self, id, name, status):
        self.id = id
        self.name = name
        self.staus = status


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/init', methods=["POST"])
def init():
    mongo.db.timetable.delete_many({})
    data = request.get_json()
    course_list = []
    lecturer_list = []
    student_group_list = []
    rooms_list = []
    days_list = []
    hours_list = []
    no_of_days = -1
    no_of_hours = -1
    day_dictionary = {}
    hour_dictionary = {}
    lecturer_dictionary = {}
    student_group_dictionary = {}
    course_dictionary = {}
    room_dictionary = {}
    columns = {}
    hours_for_columns = {}
    rows = {}
    total_hours = 0

    count = 0
    for day in data["days"]:
        days_list.append(Day(count, day))
        count += 1
    no_of_days = count

    count = 0
    for hour in data["hours"]:
        hours_list.append(Hour(count, hour["name"], hour["status"]))
        count += 1
    no_of_hours = count

    count = 0
    for room in data["rooms"]:
        rooms_list.append(Room(count, room))
        count += 1

    count = 0
    for course in data["courses"]:
        day_count_dict = {}
        for day_index in range(no_of_days):
            day_count_dict[day_index] = 0
        course_list.append(Course(course["course_id"], course["course_name"], course["no_hours_per_week"], len(course["valid_rooms"]), course["valid_rooms"],
                                  course["max_no_hours_per_day"], course["max_consecutive_hours_per_day"], course["no_of_hours_to_schedule_when_assigning"], day_count_dict, False, False))
        count += 1

    count = 0
    for student_group in data["student_groups"]:
        student_group_list.append(Student_Group(
            count, student_group["name"], student_group["courses"]))
        count += 1

    count = 0
    for lecturer in data["lecturers"]:
        day_count_dict = {}
        for day_index in range(no_of_days):
            day_count_dict[day_index] = 0
        lecturer_list.append(Lecturer(count, lecturer["name"], lecturer["department"], lecturer["max_no_hours_per_day"], lecturer["max_no_hours_per_week"],
                                      lecturer["max_consecutive_hours"], lecturer["rank"], [int(x) for x in lecturer["Availabilty_slots"].split()], lecturer["courses"], day_count_dict))
        count += 1

    for day in days_list:
        day_dictionary[day.id] = day

    for hour in hours_list:
        hour_dictionary[hour.id] = hour

    for lecturer in lecturer_list:
        lecturer_dictionary[lecturer.id] = lecturer

    for student_group in student_group_list:
        student_group_dictionary[student_group.id] = student_group

    for course in course_list:
        course_dictionary[course.id] = course

    for room in rooms_list:
        room_dictionary[room.id] = room

    count = 0
    for lecturer in lecturer_list:
        for course in lecturer.courses:
            if "all" in course:
                course = course.split()[0]
                for student_group in student_group_list:
                    if course in student_group.courses:
                        columns[count] = {
                            "lecturer": lecturer.id, "student_group": student_group.id, "course": course, "subset": "all"}
                        hours_for_columns[count] = course_dictionary[course].no_of_hours
                        count += 1
            elif "Batch-" in course:
                course, batch = course.split()
                batch = batch.split('-')[1]
                for student_group in student_group_list:
                    if course in student_group.courses:
                        columns[count] = {"lecturer": lecturer.id, "student_group": student_group.id,
                                          "course": course, "subset": "batch", "batch": batch}
                        hours_for_columns[count] = course_dictionary[course].no_of_hours
                        count += 1
            elif "Group" in course:
                course, group = course.split()
                group = group.split('_')[1]
                for student_group in student_group_list:
                    if course in student_group.courses:
                        columns[count] = {"lecturer": lecturer.id, "student_group": student_group.id,
                                          "course": course, "subset": "group", "batch": group}
                        hours_for_columns[count] = course_dictionary[course].no_of_hours
                        count += 1
    count = 0
    for room in rooms_list:
        for day in days_list:
            for hour in hours_list:
                rows[count] = {"day": day.id, "hour": hour.id, "room": room.id}
                count += 1
    column_numbers = [x for x in range(0, len(columns))]
    total_hours = 0
    for hours in hours_for_columns:
        total_hours += hours_for_columns[hours]

    # file = open("no_of_days", "wb")
    # pickle.dump(no_of_days, file)
    # file.close()

    mongo.db.timetable.insert_one({"name": "no_of_days", "value": no_of_days})

    # file = open("no_of_hours", "wb")
    # pickle.dump(no_of_hours, file)
    # file.close()

    mongo.db.timetable.insert_one(
        {"name": "no_of_hours", "value": no_of_hours})

    # file = open("day_dictionary", "wb")
    # pickle.dump(day_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(day_dictionary)
    mongo.db.timetable.insert_one(
        {"name": "day_dictionary", "value": Binary(thebytes)})

    # file = open("hour_dictionary", "wb")
    # pickle.dump(hour_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(hour_dictionary)
    mongo.db.timetable.insert_one(
        {"name": "hour_dictionary", "value": Binary(thebytes)})

    # file = open("room_dictionary", "wb")
    # pickle.dump(room_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(room_dictionary)
    mongo.db.timetable.insert_one(
        {"name": "room_dictionary", "value": Binary(thebytes)})

    # file = open("lecturer_dictionary", "wb")
    # pickle.dump(lecturer_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(lecturer_dictionary)
    mongo.db.timetable.insert_one(
        {"name": "lecturer_dictionary", "value": Binary(thebytes)})

    # file = open("student_group_dictionary", "wb")
    # pickle.dump(student_group_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(student_group_dictionary)
    mongo.db.timetable.insert_one({"name": "student_group_dictionary",
                                   "value": Binary(thebytes)})

    # file = open("course_dictionary", "wb")
    # pickle.dump(course_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(course_dictionary)
    mongo.db.timetable.insert_one(
        {"name": "course_dictionary", "value": Binary(thebytes)})

    # file = open("columns", "wb")
    # pickle.dump(columns, file)
    # file.close()

    thebytes = pickle.dumps(columns)
    mongo.db.timetable.insert_one(
        {"name": "columns", "value": Binary(thebytes)})

    # file = open("hours_for_columns", "wb")
    # pickle.dump(hours_for_columns, file)
    # file.close()

    thebytes = pickle.dumps(hours_for_columns)
    mongo.db.timetable.insert_one(
        {"name": "hours_for_columns", "value": Binary(thebytes)})

    # file = open("rows", "wb")
    # pickle.dump(rows, file)
    # file.close()

    thebytes = pickle.dumps(rows)
    mongo.db.timetable.insert_one({"name": "rows", "value": Binary(thebytes)})

    # file = open("total_hours", "wb")
    # pickle.dump(total_hours, file)
    # file.close()

    mongo.db.timetable.insert_one(
        {"name": "total_hours", "value": total_hours})

    return {"column_numbers": column_numbers}


def getValidDays(no_of_days, rows, columns, target_matrix, lecturer_id, course_id, lecturer_max_no_hours_per_day, course_max_no_hours_per_day, lecturer_dictionary, course_dictionary):
    day_flag = [False] * no_of_days
    lecturer_day_count_dict = lecturer_dictionary[lecturer_id].day_count_dict
    course_day_count_dict = course_dictionary[course_id].day_count_dict
    for day in range(no_of_days):
        if lecturer_max_no_hours_per_day > lecturer_day_count_dict[day] and course_max_no_hours_per_day > course_day_count_dict[day]:
            day_flag[day] = True
    return day_flag


def getValidRows(rows, target_matrix, column_number, day_flag, room_dictionary, valid_rooms, no_of_hours_to_schedule_when_assigning, lecturer_availability, no_of_hours):
    valid_rows = []
    for i in range(len(rows)):
        day = rows[i]["day"]
        hour = rows[i]["hour"]
        if target_matrix[i][column_number] == 0 and day_flag[day]:
            if room_dictionary[rows[i]["room"]].name in valid_rooms:
                try:
                    flag = True
                    for j in range(no_of_hours_to_schedule_when_assigning):
                        if rows[i]['hour'] + j != rows[i+j]['hour'] or lecturer_availability[day*no_of_hours+hour+j] != 1 or target_matrix[i+j][column_number] != 0:
                            flag = False
                            break
                    if flag:
                        valid_rows.append(i)
                except:
                    pass
    return valid_rows


def no_batch_conflicts(subset, target_matrix, rows, columns, day, hour, batch, student_group_id, course_id, lecturer_id):
    for i in range(len(rows)):
        current_day = rows[i]["day"]
        current_hour = rows[i]["hour"]
        if current_day == day and current_hour == hour:
            for j in range(len(columns)):
                if columns[j]["subset"] == subset and columns[j]["student_group"] == student_group_id and target_matrix[i][j] == 1:
                    if columns[j]["batch"] == batch or columns[j]["lecturer"] == lecturer_id or columns[j]["course"] == course_id:
                        return False
    return True


def scheduleCourse(valid_rows, no_of_hours_to_schedule_when_assigning, rows, columns, target_matrix, lecturer_id, student_group_id, column_number, lecturer_dictionary, course_dictionary):
    row_id_to_schedule = random.choice(valid_rows)
    no_of_hours_scheduled = 0
    for k in range(no_of_hours_to_schedule_when_assigning):
        day = rows[row_id_to_schedule+k]["day"]
        hour = rows[row_id_to_schedule+k]["hour"]
        room = rows[row_id_to_schedule+k]["room"]

        for j in range(len(columns)):
            target_matrix[row_id_to_schedule+k][j] = -1

        for i in range(len(rows)):
            for j in range(len(columns)):
                if rows[i]["day"] == day and rows[i]["hour"] == hour and columns[j]["lecturer"] == lecturer_id and target_matrix[i][j] != 1:
                    target_matrix[i][j] = -1
                if rows[i]["day"] == day and rows[i]["hour"] == hour and columns[j]["student_group"] == student_group_id and target_matrix[i][j] != 1:
                    target_matrix[i][j] = -1
        lecturer_dictionary[lecturer_id].day_count_dict[day] += 1
        course_dictionary[columns[column_number]
                          ["course"]].day_count_dict[day] += 1
        target_matrix[row_id_to_schedule+k][column_number] = 1
        no_of_hours_scheduled += 1
    return target_matrix, no_of_hours_scheduled


def fillTargetMatrix(target_matrix_template, column_numbers, columns, hours_for_columns, rows, day_dictionary, hour_dictionary, room_dictionary, lecturer_dictionary, student_group_dictionary, course_dictionary, no_of_days, no_of_hours, total_hours):
    target_matrix = target_matrix_template
    no_hours_not_scheduled = 0
    for column_number in column_numbers:
        if columns[column_number]["subset"] == "all":
            course_id = columns[column_number]['course']
            lecturer_id = columns[column_number]['lecturer']
            student_group_id = columns[column_number]['student_group']
            no_of_hours_to_schedule = hours_for_columns[column_number]
            no_of_hours_to_schedule_when_assigning = course_dictionary[
                course_id].no_of_hours_to_schedule_when_assigning
            while no_of_hours_to_schedule > 0:
                day_flag = getValidDays(no_of_days, rows, columns, target_matrix, lecturer_id, course_id,
                                        lecturer_dictionary[lecturer_id].max_no_hours_per_day, course_dictionary[course_id].max_no_hours_per_day, lecturer_dictionary, course_dictionary)

                valid_rows = getValidRows(rows, target_matrix, column_number, day_flag, room_dictionary,
                                          course_dictionary[course_id].valid_rooms, no_of_hours_to_schedule_when_assigning, lecturer_dictionary[lecturer_id].availability, no_of_hours)
                # print(column_number, day_flag, valid_rows)
                if len(valid_rows) == 0:
                    no_hours_not_scheduled += no_of_hours_to_schedule
                    break

                target_matrix, no_of_hours_scheduled = scheduleCourse(
                    valid_rows, no_of_hours_to_schedule_when_assigning, rows, columns, target_matrix, lecturer_id, student_group_id, column_number, lecturer_dictionary, course_dictionary)
                no_of_hours_to_schedule -= no_of_hours_scheduled

        else:
            course_id = columns[column_number]['course']
            lecturer_id = columns[column_number]['lecturer']
            student_group_id = columns[column_number]['student_group']
            no_of_hours_to_schedule = hours_for_columns[column_number]
            batch = columns[column_number]["batch"]
            subset = columns[column_number]["subset"]
            no_of_hours_to_schedule_when_assigning = course_dictionary[
                course_id].no_of_hours_to_schedule_when_assigning
            while no_of_hours_to_schedule > 0:
                day_flag = getValidDays(no_of_days, rows, columns, target_matrix, lecturer_id, course_id,
                                        lecturer_dictionary[lecturer_id].max_no_hours_per_day, course_dictionary[course_id].max_no_hours_per_day, lecturer_dictionary, course_dictionary)
                valid_rows = getValidRows(rows, target_matrix, column_number, day_flag, room_dictionary,
                                          course_dictionary[course_id].valid_rooms, no_of_hours_to_schedule_when_assigning, lecturer_dictionary[lecturer_id].availability, no_of_hours)
                # print(column_number, day_flag, valid_rows)
                if len(valid_rows) == 0:
                    no_hours_not_scheduled += no_of_hours_to_schedule
                    break
                scheduled_flag = False
                for i in range(len(rows)):
                    day = rows[i]["day"]
                    hour = rows[i]["hour"]
                    for j in range(len(columns)):
                        if columns[j]["subset"] == subset and columns[j]["student_group"] == student_group_id:
                            if columns[j]["batch"] != subset and columns[j]["course"] != course_id and target_matrix[i][j] == 1:
                                batch_has_not_been_scheduled_flag = True
                                if no_batch_conflicts(subset, target_matrix, rows, columns, day, hour, batch, student_group_id, course_id, lecturer_id):
                                    for o in valid_rows:
                                        if rows[o]["day"] == day and rows[o]["hour"] == hour and target_matrix[o][column_number] == 0:
                                            for k in range(no_of_hours_to_schedule_when_assigning):
                                                for l in range(len(columns)):
                                                    target_matrix[o+k][l] = -1
                                                for m in range(len(rows)):
                                                    for n in range(len(columns)):
                                                        if rows[m]["day"] == rows[o+k]["day"] and rows[m]["hour"] == rows[o+k]["hour"] and columns[n]["lecturer"] == lecturer_id and target_matrix[m][n] != 1:
                                                            target_matrix[m][n] = -1
                                                        if rows[m]["day"] == rows[o+k]["day"] and rows[m]["hour"] == rows[o+k]["hour"] and columns[n]["student_group"] == student_group_id and columns[n]["subset"] != subset and target_matrix[m][n] != 1:
                                                            target_matrix[m][n] = -1
                                                        if rows[m]["day"] == rows[o+k]["day"] and rows[m]["hour"] == rows[o+k]["hour"] and columns[n]["student_group"] == student_group_id and columns[n]["subset"] == subset and columns[n]["batch"] == batch and target_matrix[m][n] != 1:
                                                            target_matrix[m][n] = -1
                                                lecturer_dictionary[lecturer_id].day_count_dict[rows[o+k]["day"]] += 1
                                                course_dictionary[columns[column_number]["course"]
                                                                  ].day_count_dict[rows[o+k]["day"]] += 1
                                                target_matrix[o +
                                                              k][column_number] = 1
                                                scheduled_flag = True
                                                no_of_hours_to_schedule -= 1
                                            break
                                if scheduled_flag:
                                    break
                            if scheduled_flag:
                                break

                if scheduled_flag == False:
                    row_id_to_schedule = random.choice(valid_rows)
                    scheduled_rows = []
                    for k in range(no_of_hours_to_schedule_when_assigning):
                        day = rows[row_id_to_schedule+k]["day"]
                        hour = rows[row_id_to_schedule+k]["hour"]

                        for j in range(len(columns)):
                            target_matrix[row_id_to_schedule+k][j] = -1

                        for i in range(len(rows)):
                            for j in range(len(columns)):
                                if i not in scheduled_rows:
                                    if rows[i]["day"] == day and rows[i]["hour"] == hour and columns[j]["lecturer"] == lecturer_id and target_matrix[i][j] != 1:
                                        target_matrix[i][j] = -1
                                    if rows[i]["day"] == day and rows[i]["hour"] == hour and columns[j]["student_group"] == student_group_id and columns[j]["subset"] != subset and target_matrix[i][j] != 1:
                                        target_matrix[i][j] = -1
                                    if rows[i]["day"] == day and rows[i]["hour"] == hour and columns[j]["student_group"] == student_group_id and columns[j]["subset"] == subset and columns[j]["batch"] == batch and target_matrix[i][j] != 1:
                                        target_matrix[i][j] = -1
                        lecturer_dictionary[lecturer_id].day_count_dict[day] += 1
                        course_dictionary[columns[column_number]
                                          ["course"]].day_count_dict[day] += 1
                        target_matrix[row_id_to_schedule+k][column_number] = 1
                        scheduled_rows.append(row_id_to_schedule+k)
                        no_of_hours_to_schedule -= 1
    return target_matrix, 100 - (no_hours_not_scheduled * 100)/total_hours


@app.route("/fill_target_matrix", methods=["POST"])
def handle_fill_target_matrix():
    import time
    time.sleep(.5)
    return {"status": "done"}
    data = request.get_json()

    print(data)
    # file = open("no_of_days", "rb")
    # no_of_days = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "no_of_days"})
    no_of_days = res["value"]

    # file = open("no_of_hours", "rb")
    # no_of_hours = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "no_of_hours"})
    no_of_hours = res["value"]

    # file = open("day_dictionary", "rb")
    # day_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "day_dictionary"})
    day_dictionary = pickle.loads(res["value"])

    # file = open("hour_dictionary", "rb")
    # hour_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "hour_dictionary"})
    hour_dictionary = pickle.loads(res["value"])

    # file = open("room_dictionary", "rb")
    # room_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "room_dictionary"})
    room_dictionary = pickle.loads(res["value"])

    # file = open("lecturer_dictionary", "rb")
    # lecturer_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "lecturer_dictionary"})
    lecturer_dictionary = pickle.loads(res["value"])

    # file = open("student_group_dictionary", "rb")
    # student_group_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "student_group_dictionary"})
    student_group_dictionary = pickle.loads(res["value"])

    # file = open("course_dictionary", "rb")
    # course_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "course_dictionary"})
    course_dictionary = pickle.loads(res["value"])

    # file = open("columns", "rb")
    # columns = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "columns"})
    columns = pickle.loads(res["value"])

    # file = open("hours_for_columns", "rb")
    # hours_for_columns = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "hours_for_columns"})
    hours_for_columns = pickle.loads(res["value"])

    # file = open("rows", "rb")
    # rows = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "rows"})
    rows = pickle.loads(res["value"])

    # file = open("total_hours", "rb")
    # total_hours = pickle.load(file)
    # file.close()

    name = data["name"]
    chromosome_to_fitness_dictionary = {}
    chromosome_to_target_matrix_dictionary = {}

    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_fitness_dictionary"})
    if res is not None:
        chromosome_to_fitness_dictionary = pickle.loads(res["value"])

    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_target_matrix_dictionary"})
    if res is not None:
        chromosome_to_target_matrix_dictionary = pickle.loads(res["value"])

    print("Length of dictionary is: ", len(chromosome_to_fitness_dictionary))

    # if os.path.exists(name + "_chromosome_to_fitness_dictionary"):
    #     file = open(name + "_chromosome_to_fitness_dictionary", "rb")
    #     chromosome_to_fitness_dictionary = pickle.load(file)
    #     file.close()
    #     file = open(name+"_chromosome_to_target_matrix_dictionary", "rb")
    #     chromosome_to_target_matrix_dictionary = pickle.load(file)
    #     file.close()

    column_numbers = data["column_numbers"]
    target_matrix_template = np.zeros((len(rows), len(columns)))
    for i in range(len(rows)):
        if rows[i]["hour"] == 2 or rows[i]["hour"] == 5:
            for j in range(len(columns)):
                target_matrix_template[i][j] = -1
    target_matrix, fitness = fillTargetMatrix(target_matrix_template, column_numbers, columns, hours_for_columns, rows, day_dictionary,
                                              hour_dictionary, room_dictionary, lecturer_dictionary, student_group_dictionary, course_dictionary, no_of_days, no_of_hours, total_hours=210)
    chromosome_to_fitness_dictionary[tuple(column_numbers)] = fitness
    chromosome_to_target_matrix_dictionary[tuple(
        column_numbers)] = target_matrix

    # file = open(name + "_chromosome_to_fitness_dictionary", "wb")
    # pickle.dump(chromosome_to_fitness_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(chromosome_to_fitness_dictionary)
    mongo.db.timetable.update_one({"name": name + "_chromosome_to_fitness_dictionary"},
                                  {"$set": {"value": Binary(thebytes)}}, upsert=True)

    # file = open(name+"_chromosome_to_target_matrix_dictionary", "wb")
    # pickle.dump(chromosome_to_target_matrix_dictionary, file)
    # file.close()

    thebytes = pickle.dumps(chromosome_to_target_matrix_dictionary)
    mongo.db.timetable.update_one({"name": name+"_chromosome_to_target_matrix_dictionary"},
                                  {"$set": {"value": Binary(thebytes)}}, upsert=True)

    return {"status": "done"}


def elitism_selection(data, percentage):
    my_list = []
    number_of_elements_to_select = int((percentage/100)*len(data))
    for k, v in data.items():
        my_list.append((k, v))
    elements_selected = sorted(my_list, key=lambda x: x[1], reverse=True)[
        0:number_of_elements_to_select]
    return_elements = []
    for element in elements_selected:
        return_elements.append(list(element[0]))
    return return_elements


def selection(data):
    sum_fittness = sum(data.values())
    partial = 0
    rand = random.randrange(0, int(sum_fittness))
    # print(rand)
    for k, v in data.items():
        # print(k)
        partial = partial+v
        if (partial >= rand):
            return list(k)


def mutation(chromosome, n):
    numbers = {}
    index_of_duplicates = []
    for i in range(n):
        numbers[i] = 0
    for i in range(len(chromosome)):
        if numbers[chromosome[i]] == 0:
            numbers[chromosome[i]] = 1
        elif numbers[chromosome[i]] == 1:
            index_of_duplicates.append(i)
    list_of_numbers_not_included = []
    print(numbers)
    for key, value in numbers.items():
        if value == 0:
            list_of_numbers_not_included.append(key)

    for index in index_of_duplicates:
        chromosome[index] = list_of_numbers_not_included.pop()
    return chromosome


def crossover(parent1, parent2):
    length = len(parent1)
    crosspoint1 = random.randrange(1, length-1)
    crosspoint2 = random.randrange(crosspoint1+1, length)
    print(crosspoint1, crosspoint2)
    child1 = parent1[0:crosspoint1] + \
        parent2[crosspoint1:crosspoint2]+parent1[crosspoint2:length]
    child2 = parent2[0:crosspoint1] + \
        parent1[crosspoint1:crosspoint2]+parent2[crosspoint2:length]
    return child1, child2


def geneticAlgorithm(prev_population, number_of_population):
    new_population = elitism_selection(prev_population, 10)
    for i in range(number_of_population//2 - len(new_population)//2):
        parent1 = selection(prev_population)
        parent2 = selection(prev_population)
        child1, child2 = crossover(parent1, parent2)
        child1 = mutation(child1, len(child1))
        child2 = mutation(child2, len(child2))
        new_population.append(child1)
        new_population.append(child2)
    return new_population[:number_of_population]


@app.route("/genetic_algorithm", methods=["POST"])
def create_new_population():
    data = request.get_json()
    name = data["name"]
    population_size = data["population_size"]
    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_fitness_dictionary"})
    chromosome_to_fitness_dictionary = pickle.loads(res["value"])
    # file.close()
    # print(data)
    # population_size = data["population_size"]
    # data = data["chromosome_to_fitness_dictionary"]
    # chromosome_to_fitness_dictionary = {}
    # for key, val in data.items():
    #     chromosome_to_fitness_dictionary[ast.literal_eval(key)] = val
    # print(chromosome_to_fitness_dictionary)
    new_population = geneticAlgorithm(
        chromosome_to_fitness_dictionary, population_size)

    return {"new_population": new_population}


@app.route("/create_initial_population", methods=["POST"])
def create_initial_population():
    data = request.get_json()
    print(data)
    column_numbers = ast.literal_eval(data["column_numbers"])
    population = []
    for x in range(data["population_size"]):
        q = column_numbers.copy()
        random.shuffle(q)
        population.append(q)
    return {"population": population}


@app.route("/get_performance", methods=["POST"])
def get_performance():
    data = request.get_json()
    name = data["name"]

    # file = open(name+'_chromosome_to_fitness_dictionary', 'rb')
    # chromosome_to_fitness_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_fitness_dictionary"})
    chromosome_to_fitness_dictionary = pickle.loads(res["value"])

    summation = 0
    maximum = 0
    minimum = 100
    for i in chromosome_to_fitness_dictionary.values():
        if i > maximum:
            maximum = i
        if i < minimum:
            minimum = i
        summation += i
    average = summation/len(chromosome_to_fitness_dictionary)
    return {"maximum": maximum, "minimum": minimum, "average": average}


@app.route("/get_chromosome_with_maximum", methods=["POST"])
def get_chromosome_with_maximum():
    data = request.get_json()
    name = data["name"]

    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_fitness_dictionary"})
    chromosome_to_fitness_dictionary = pickle.loads(res["value"])

    maximum = 0
    for i in chromosome_to_fitness_dictionary:
        if maximum < chromosome_to_fitness_dictionary[i]:
            maximum = chromosome_to_fitness_dictionary[i]
            maximum_chromosome = i

    return {"chromosome": str(maximum_chromosome)}


def make_html_timetable(rows, columns, className, classId, target_matrix, no_of_days, no_of_hours, course_dictionary, lecturer_dictionary, room_dictionary, hour_dictionary, day_dictionary):
    lectures = []
    for i in range(len(rows)):
        for j in range(len(columns)):
            if className == "room":
                if rows[i]["room"] == classId and target_matrix[i][j] == 1:
                    lectures.append((i, j))
            else:
                if columns[j][className] == classId and target_matrix[i][j] == 1:
                    lectures.append((i, j))

    slots = {}
    for i in range(no_of_days):
        for j in range(no_of_hours):
            slots[(i, j)] = []

    for i, j in lectures:
        slots[(rows[i]["day"], rows[i]["hour"])].append((rows[i], columns[j]))

    html_slots = {}
    for key, val in slots.items():
        temp_list = []
        try:
            val = sorted(val, key=lambda item: item[1]["batch"])
        except:
            pass
        for item in val:
            if item[1]["subset"] == "all":
                temp_list.append(course_dictionary[item[1]["course"]].name + " " +
                                 lecturer_dictionary[item[1]["lecturer"]].name+" " + room_dictionary[item[0]["room"]].name)
            else:
                temp_list.append(course_dictionary[item[1]["course"]].name + " " + lecturer_dictionary[item[1]
                                                                                                       ["lecturer"]].name+" " + room_dictionary[item[0]["room"]].name + " "+item[1]["batch"])
        if len(temp_list) == 0:
            temp_list.append("Free")
        html_slots[key] = temp_list
    html_page = '''
      <table>
      <style type="text/css">
      table,
      th,
      td {
        border: 3px solid #ff2e63;
      }
    </style>
      <tr>
            <th>
              Day
            </th>
    '''
    for j in range(no_of_hours):
        html_page += "<th>"+hour_dictionary[j].name+"</th>"
    html_page += "</tr>"
    for i in range(no_of_days):
        html_page += "<tr><td>"+day_dictionary[i].name+"</td>"
        count = 1
        for j in range(no_of_hours):
            items = html_slots[(i, j)]
            if len(items) == 1:
                html_page += "<td>" + items[0]+"</td>"
            else:
                if j+1 != no_of_hours:
                    if html_slots[(i, j)] == html_slots[(i, j+1)]:
                        count += 1
                    else:
                        html_page += "<td colspan=" + \
                            str(count)+">"+"<table style=\"width: 100%;\">"
                        for item in items:
                            html_page += "<tr><td>" + item + "</td></tr>"
                        html_page += "</table></td>"
                        count = 1
                else:
                    html_page += "<td colspan=" + \
                        str(count)+">"+"<table style=\"width: 100%;\">"
                    for item in items:
                        html_page += "<tr><td>" + item + "</td></tr>"
                    html_page += "</table></td>"
                    count = 1
        html_page += "</tr>"
    html_page += "</table>"
    return html_page


@app.route("/get_timetable", methods=["POST"])
def get_timetable():
    data = request.get_json()
    print(data)
    name = data["name"]
    chromosome = ast.literal_eval(data["chromosome"])
    className = data["className"]
    classId = data["classId"]

    res = mongo.db.timetable.find_one({"name": "no_of_days"})
    no_of_days = res["value"]

    # file = open("no_of_hours", "rb")
    # no_of_hours = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "no_of_hours"})
    no_of_hours = res["value"]

    # file = open("day_dictionary", "rb")
    # day_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "day_dictionary"})
    day_dictionary = pickle.loads(res["value"])

    # file = open("hour_dictionary", "rb")
    # hour_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "hour_dictionary"})
    hour_dictionary = pickle.loads(res["value"])

    # file = open("room_dictionary", "rb")
    # room_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "room_dictionary"})
    room_dictionary = pickle.loads(res["value"])

    # file = open("lecturer_dictionary", "rb")
    # lecturer_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "lecturer_dictionary"})
    lecturer_dictionary = pickle.loads(res["value"])

    # file = open("student_group_dictionary", "rb")
    # student_group_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "student_group_dictionary"})
    student_group_dictionary = pickle.loads(res["value"])

    # file = open("course_dictionary", "rb")
    # course_dictionary = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "course_dictionary"})
    course_dictionary = pickle.loads(res["value"])

    # file = open("columns", "rb")
    # columns = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "columns"})
    columns = pickle.loads(res["value"])

    # file = open("hours_for_columns", "rb")
    # hours_for_columns = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "hours_for_columns"})
    hours_for_columns = pickle.loads(res["value"])

    # file = open("rows", "rb")
    # rows = pickle.load(file)
    # file.close()

    res = mongo.db.timetable.find_one({"name": "rows"})
    rows = pickle.loads(res["value"])

    res = mongo.db.timetable.find_one(
        {"name": name + "_chromosome_to_target_matrix_dictionary"})
    chromosome_to_target_matrix_dictionary = pickle.loads(res["value"])

    target_matrix = chromosome_to_target_matrix_dictionary[chromosome]

    if className == "lecturer":
        for key, value in lecturer_dictionary.items():
            if value.name == classId:
                classId = key
                break

    elif className == "student_group":
        for key, value in student_group_dictionary.items():
            if value.name == classId:
                classId = key
                break

    elif className == "room":
        for key, value in room_dictionary.items():
            if value.name == classId:
                classId = key
                break

    page = make_html_timetable(rows, columns, className, classId, target_matrix, no_of_days, no_of_hours,
                               course_dictionary, lecturer_dictionary, room_dictionary, hour_dictionary, day_dictionary)

    return page


if __name__ == '__main__':
    app.run(debug=True)
