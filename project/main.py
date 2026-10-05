"""
پروژه مدیریت نمرات دانش‌آموزان کلاس اول
دبستان دخترانه جوانه‌های ایران
"""

from abc import ABC, abstractmethod
import sqlite3
import random
import os
import sys


# ============================================================
# 1) کلاس انتزاعی Person  (Abstraction)
# ============================================================
class Person(ABC):
    def __init__(self, national_id, first_name, last_name, age):
        self._national_id = national_id
        self._first_name = first_name
        self._last_name = last_name
        self._age = age

    @property
    def national_id(self): return self._national_id
    @property
    def first_name(self): return self._first_name
    @property
    def last_name(self):  return self._last_name
    @property
    def age(self):        return self._age
    @property
    def full_name(self):  return f"{self._first_name} {self._last_name}"

    @abstractmethod
    def role(self): ...

    def __str__(self):
        return f"[{self.role()}] {self.full_name}"

    def __repr__(self):
        return (f"{self.__class__.__name__}(national_id='{self._national_id}', "
                f"first_name='{self._first_name}', last_name='{self._last_name}', age={self._age})")


# ============================================================
# 2) کلاس Student (Inheritance از Person)
# ============================================================
class Student(Person):
    def __init__(self, national_id, first_name, last_name, age,
                 student_code, classroom="اول"):
        super().__init__(national_id, first_name, last_name, age)
        self._student_code = student_code
        self._classroom = classroom
        self._grades = {}

    @property
    def student_code(self): return self._student_code
    @property
    def classroom(self):    return self._classroom
    @property
    def grades(self):       return dict(self._grades)

    def add_grade(self, course, score):
        if not isinstance(score, (int, float)):
            raise TypeError("نمره باید عدد باشد")
        if not 0 <= score <= 20:
            raise ValueError(f"نمره باید بین 0 تا 20 باشد (دریافت شد: {score})")
        self._grades[course] = float(score)

    def average(self):
        if not self._grades:
            return 0.0
        return sum(self._grades.values()) / len(self._grades)

    def status(self):
        return "قبول" if self.average() >= 10 else "تجدید"

    def role(self):
        return "دانش‌آموز"

    def __eq__(self, other):
        return isinstance(other, Student) and self._student_code == other._student_code

    def __hash__(self):
        return hash(self._student_code)

    def __str__(self):
        return (f"{super().__str__()} | کد: {self._student_code} | "
                f"کلاس: {self._classroom} | معدل: {self.average():.2f} | {self.status()}")


# ============================================================
# 3) کلاس Teacher
# ============================================================
class Teacher(Person):
    def __init__(self, national_id, first_name, last_name, age,
                 employee_code, subject):
        super().__init__(national_id, first_name, last_name, age)
        self._employee_code = employee_code
        self._subject = subject

    @property
    def employee_code(self): return self._employee_code
    @property
    def subject(self):       return self._subject

    def role(self):
        return "معلم"

    def __str__(self):
        return f"{super().__str__()} | کد پرسنلی: {self._employee_code} | درس: {self._subject}"


# ============================================================
# 4) کلاس Database (Singleton + SQLite)
# ============================================================
class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_name="javaneh_school.db"):
        if getattr(self, "_initialized", False):
            return
        self._db_name = db_name
        self._conn = sqlite3.connect(db_name)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._cursor = self._conn.cursor()
        self._create_tables()
        self._initialized = True

    def _create_tables(self):
        self._cursor.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                national_id  TEXT PRIMARY KEY,
                first_name   TEXT NOT NULL,
                last_name    TEXT NOT NULL,
                age          INTEGER NOT NULL,
                student_code TEXT UNIQUE NOT NULL,
                classroom    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS grades (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_code TEXT NOT NULL,
                course       TEXT NOT NULL,
                score        REAL NOT NULL CHECK(score >= 0 AND score <= 20),
                UNIQUE(student_code, course),
                FOREIGN KEY (student_code) REFERENCES students(student_code)
                    ON DELETE CASCADE
            );
        """)
        self._conn.commit()

    def save_student(self, student):
        self._cursor.execute("""
            INSERT OR REPLACE INTO students
            (national_id, first_name, last_name, age, student_code, classroom)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student.national_id, student.first_name, student.last_name,
              student.age, student.student_code, student.classroom))
        self._conn.commit()

    def save_grade(self, student_code, course, score):
        self._cursor.execute("""
            INSERT OR REPLACE INTO grades (student_code, course, score)
            VALUES (?, ?, ?)
        """, (student_code, course, float(score)))
        self._conn.commit()

    def get_grades(self, student_code):
        self._cursor.execute(
            "SELECT course, score FROM grades WHERE student_code=? ORDER BY course",
            (student_code,))
        return self._cursor.fetchall()

    def get_all_students(self):
        """همه دانش‌آموزان رو از دیتابیس می‌خونه"""
        self._cursor.execute("""
            SELECT national_id, first_name, last_name, age, student_code, classroom
            FROM students
            ORDER BY student_code
        """)
        return self._cursor.fetchall()

    def count_students(self):
        self._cursor.execute("SELECT COUNT(*) FROM students")
        return self._cursor.fetchone()[0]

    def count_grades(self):
        self._cursor.execute("SELECT COUNT(*) FROM grades")
        return self._cursor.fetchone()[0]

    def top_students(self, n=5):
        self._cursor.execute("""
            SELECT s.student_code, s.first_name, s.last_name,
                   ROUND(AVG(g.score), 2) AS avg_score
            FROM students s
            JOIN grades g ON s.student_code = g.student_code
            GROUP BY s.student_code
            ORDER BY avg_score DESC
            LIMIT ?
        """, (n,))
        return self._cursor.fetchall()

    def class_average(self):
        self._cursor.execute("SELECT AVG(score) FROM grades")
        return self._cursor.fetchone()[0] or 0.0

    def course_averages(self):
        self._cursor.execute("""
            SELECT course, ROUND(AVG(score), 2), COUNT(*)
            FROM grades GROUP BY course
        """)
        return self._cursor.fetchall()

    def status_summary(self):
        self._cursor.execute("""
            SELECT
              SUM(CASE WHEN avg_score >= 10 THEN 1 ELSE 0 END) AS passed,
              SUM(CASE WHEN avg_score <  10 THEN 1 ELSE 0 END) AS failed
            FROM (
              SELECT student_code, AVG(score) AS avg_score
              FROM grades GROUP BY student_code
            )
        """)
        return self._cursor.fetchone()

    def close(self):
        self._conn.close()
        Database._instance = None


# ============================================================
# 5) کلاس School (Composition)
# ============================================================
class School:
    def __init__(self, name, principal_name):
        self._name = name
        self._principal_name = principal_name
        self._students = []
        self._teachers = []
        self._db = Database()

    @property
    def name(self):   return self._name
    @property
    def db(self):     return self._db

    def add_student(self, student):
        if not isinstance(student, Student):
            raise TypeError("فقط نمونه‌ی Student قابل افزودن است")
        if student in self._students:
            raise ValueError(f"دانش‌آموز با کد {student.student_code} قبلاً ثبت شده است")
        self._students.append(student)
        self._db.save_student(student)

    def add_teacher(self, teacher):
        if not isinstance(teacher, Teacher):
            raise TypeError("فقط نمونه‌ی Teacher قابل افزودن است")
        self._teachers.append(teacher)

    def load_from_db(self):
        """دانش‌آموزان و نمراتشون رو از دیتابیس بارگذاری می‌کنه"""
        self._students.clear()
        for row in self._db.get_all_students():
            national_id, fn, ln, age, code, classroom = row
            student = Student(national_id, fn, ln, age, code, classroom)
            for course, score in self._db.get_grades(code):
                student.add_grade(course, score)
            self._students.append(student)

    def register_grade(self, student, course, score):
        if student not in self._students:
            raise ValueError("این دانش‌آموز در مدرسه ثبت نشده است")
        student.add_grade(course, score)
        self._db.save_grade(student.student_code, course, score)

    def find_by_code(self, code):
        for s in self._students:
            if s.student_code == code:
                return s
        return None

    def __len__(self):        return len(self._students)
    def __iter__(self):       return iter(self._students)
    def __getitem__(self, i): return self._students[i]
    def __contains__(self, s):return s in self._students
    def __str__(self):
        return f"مدرسه {self._name} | مدیر: {self._principal_name} | تعداد: {len(self)}"


# ============================================================
# 6) داده‌های اولیه و runner
# ============================================================
GIRLS_FIRST_NAMES = [
    "زهرا","فاطمه","مریم","نرگس","سارا","ریحانه","نازنین","یاسمین","هستی","النا",
    "آوا","باران","ترنم","دنیا","رها","ستایش","شایلی","طناز","عسل","غزل",
    "فرشته","کیانا","لیانا","مهسا","نازلی","نیایش","ونوس","هدیه","یلدا","آرزو",
    "بهاره","پریسا","ترانه","حدیث","خاطره","درسا","رعنا","زیبا","سمانه","شبنم",
    "صبا","ضحی","طاهره","عاطفه","فرناز","کیمیا","گلنار","لاله","مبینا","نسترن",
]

LAST_NAMES = [
    "احمدی","محمدی","حسینی","رضایی","موسوی","کریمی","صادقی","جعفری","نوری","قاسمی",
    "رستمی","شریفی","اکبری","عباسی","یوسفی","هاشمی","مرادی","فتحی","سلطانی","نجفی",
]

COURSES = ["ریاضی", "فارسی", "علوم", "قرآن", "هنر"]


def seed_school(school: School):
    """اگه دیتابیس خالی بود داده اولیه می‌سازه، وگرنه بارگذاری می‌کنه"""
    existing = school.db.count_students()

    if existing > 0:
        print(f"📂 دیتابیس موجود پیدا شد ({existing} دانش‌آموز). داده‌ها بارگذاری می‌شوند...")
        school.load_from_db()
        print(f"✅ {len(school)} دانش‌آموز از دیتابیس بازیابی شد.\n")
        return

    print("🌱 دیتابیس خالی است. داده‌های اولیه ساخته می‌شوند...")
    random.seed(1403)
    for i in range(1, 51):
        student = Student(
            national_id=f"{1000000000 + i}",
            first_name=GIRLS_FIRST_NAMES[i - 1],
            last_name=LAST_NAMES[(i - 1) % len(LAST_NAMES)],
            age=7,
            student_code=f"1403-{i:03d}",
            classroom="اول",
        )
        school.add_student(student)
        for course in COURSES:
            score = round(random.uniform(9, 20), 1)
            school.register_grade(student, course, score)
    print(f"✅ {len(school)} دانش‌آموز و {school.db.count_grades()} نمره ثبت شد.\n")


def run_tests(school: School):
    print("=" * 60)
    print("🧪 شروع تست‌های خودکار")
    print("=" * 60)

    assert len(school) == 50
    print(f"✅ تست 1: تعداد دانش‌آموزان = {len(school)}")

    grade_count = school.db.count_grades()
    assert grade_count == 50 * len(COURSES)
    print(f"✅ تست 2: تعداد نمرات در دیتابیس = {grade_count}")

    db2 = Database()
    assert db2 is school.db
    print("✅ تست 3: الگوی Singleton دیتابیس تأیید شد")

    s = school[0]
    try:
        s.add_grade("ریاضی", 25); assert False
    except ValueError:
        print("✅ تست 4: اعتبارسنجی نمره (Encapsulation)")

    assert all(st.role() == "دانش‌آموز" for st in school)
    print("✅ تست 5: چندریختی role() کار می‌کند")

    assert 0 <= school[0].average() <= 20
    print(f"✅ تست 6: معدل {school[0].full_name} = {school[0].average():.2f}")

    s_dup = Student(s.national_id, s.first_name, s.last_name, 7, s.student_code)
    assert s == s_dup
    print("✅ تست 7: __eq__ روی کد دانش‌آموزی کار می‌کند")

    try:
        school.add_student(s_dup); assert False
    except ValueError:
        print("✅ تست 8: جلوگیری از ثبت دانش‌آموز تکراری")

    try:
        school.add_student("not a student"); assert False
    except TypeError:
        print("✅ تست 9: TypeError برای ورودی نامعتبر")

    try:
        Person("1", "a", "b", 10); assert False
    except TypeError:
        print("✅ تست 10: نمی‌توان از کلاس انتزاعی Person نمونه ساخت")

    print("=" * 60)
    print("🎉 همه ۱۰ تست با موفقیت گذشتند!")
    print("=" * 60)


def print_report(school: School):
    print()
    print("=" * 60)
    print(f"📊 گزارش عملکرد {school.name}")
    print("=" * 60)
    print(f"مدیر: {school._principal_name}")
    print(f"تعداد دانش‌آموزان: {len(school)}")
    print(f"تعداد نمرات ثبت‌شده: {school.db.count_grades()}")
    print(f"میانگین کلاس: {school.db.class_average():.2f}")

    print("\n📚 میانگین هر درس:")
    for course, avg, cnt in school.db.course_averages():
        print(f"   • {course}: {avg:.2f}   ({cnt} نمره)")

    print("\n🏆 ۵ دانش‌آموز برتر:")
    for rank, (code, fn, ln, avg) in enumerate(school.db.top_students(5), 1):
        print(f"   {rank}. {fn} {ln}  (کد {code})  →  معدل {avg:.2f}")

    passed, failed = school.db.status_summary()
    print(f"\n✅ قبول: {passed} نفر   |   ❌ تجدید: {failed} نفر")
    print("=" * 60)

    print("\n👧 نمونه‌ای از دانش‌آموزان:")
    for s in list(school)[:4]:
        print("  ", s)
    print("   ...")
    for s in list(school)[-2:]:
        print("  ", s)


def main():
    db_file = "javaneh_school.db"
    reset = "--reset" in sys.argv

    if reset and os.path.exists(db_file):
        os.remove(db_file)
        print("🗑️  حالت ریست فعال شد — دیتابیس قبلی پاک شد.\n")

    school = School("دبستان دخترانه جوانه‌های ایران", "خانم مدیرزاده")
    school.add_teacher(Teacher("2001", "مینا", "کاظمی", 35, "T-001", "ریاضی"))
    school.add_teacher(Teacher("2002", "سمیرا", "رستمی", 40, "T-002", "فارسی"))

    seed_school(school)
    run_tests(school)
    print_report(school)

    school.db.close()


if __name__ == "__main__":
    main()