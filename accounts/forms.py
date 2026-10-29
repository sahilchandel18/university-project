from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser, StudentProfile, StaffProfile

class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. rahul_sharma'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. rahul@university.edu.in'})
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password (min 6 characters)'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )

    # Student Profile fields
    roll_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2022CSE045'})
    )
    registration_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. REG/2022/8941'})
    )
    course = forms.ChoiceField(
        choices=[
            ('B.Tech (Computer Science & Engineering)', 'B.Tech (Computer Science & Engineering)'),
            ('B.Tech (Information Technology)', 'B.Tech (Information Technology)'),
            ('B.Tech (Electronics & Communication)', 'B.Tech (Electronics & Communication)'),
            ('B.Tech (Mechanical Engineering)', 'B.Tech (Mechanical Engineering)'),
            ('B.Tech (Civil Engineering)', 'B.Tech (Civil Engineering)'),
            ('B.Tech (Electrical Engineering)', 'B.Tech (Electrical Engineering)'),
            ('M.Tech (Computer Science)', 'M.Tech (Computer Science)'),
            ('MCA (Master of Computer Applications)', 'MCA (Master of Computer Applications)'),
            ('MBA (Master of Business Administration)', 'MBA (Master of Business Administration)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    branch = forms.CharField(
        max_length=100,
        initial="Computer Science & Engineering",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch / Discipline'})
    )
    semester = forms.ChoiceField(
        choices=[
            ('8th Semester (Final Year)', '8th Semester (Final Year)'),
            ('7th Semester', '7th Semester'),
            ('6th Semester', '6th Semester'),
            ('4th Semester (PG)', '4th Semester (PG)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    batch_year = forms.CharField(
        max_length=30,
        initial="2022 - 2026",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2022 - 2026'})
    )
    academic_session = forms.CharField(
        max_length=20,
        initial="2025-2026",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2025-2026'})
    )
    is_hostel_resident = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    hostel_details = forms.CharField(
        required=False,
        initial="Day Scholar",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hostel Name & Room No or Day Scholar'})
    )
    contact_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'})
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def clean_confirm_password(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2

    def clean_roll_number(self):
        roll = self.cleaned_data.get('roll_number')
        if StudentProfile.objects.filter(roll_number__iexact=roll).exists():
            raise forms.ValidationError("This Roll Number is already registered.")
        return roll

    def clean_registration_number(self):
        reg = self.cleaned_data.get('registration_number')
        if StudentProfile.objects.filter(registration_number__iexact=reg).exists():
            raise forms.ValidationError("This Registration / Enrollment Number is already registered.")
        return reg

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = CustomUser.ROLE_STUDENT
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                roll_number=self.cleaned_data['roll_number'].strip().upper(),
                registration_number=self.cleaned_data['registration_number'].strip().upper(),
                course=self.cleaned_data['course'],
                branch=self.cleaned_data['branch'],
                semester=self.cleaned_data['semester'],
                batch_year=self.cleaned_data['batch_year'],
                academic_session=self.cleaned_data['academic_session'],
                is_hostel_resident=self.cleaned_data['is_hostel_resident'],
                hostel_details=self.cleaned_data['hostel_details'],
                contact_number=self.cleaned_data['contact_number'],
            )
        return user


class StudentProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = StudentProfile
        fields = ['course', 'branch', 'semester', 'batch_year', 'academic_session', 'is_hostel_resident', 'hostel_details', 'father_name', 'address', 'contact_number']
        widgets = {
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'semester': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_year': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_session': forms.TextInput(attrs={'class': 'form-control'}),
            'is_hostel_resident': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hostel_details': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
