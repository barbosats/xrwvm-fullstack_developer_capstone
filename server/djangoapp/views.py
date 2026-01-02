# Uncomment the required imports before adding the code

import json
import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import User
from django.http import JsonResponse

# from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import CarMake, CarModel
from .populate import initiate
from .restapis import get_request, post_review

# from .restapis import analyze_review_sentiments


logger = logging.getLogger(__name__)


# Login view
@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    username = data.get("userName")
    password = data.get("password")
    user = authenticate(username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({"userName": username, "status": "Authenticated"})
    return JsonResponse({"status": "unauthorized"}, status=401)


# Logout view
@csrf_exempt
def logout_request(request):
    django_logout(request)  # encerra sessão
    return JsonResponse({"userName": ""})


# Registration view
@csrf_exempt
def registration(request):
    data = json.loads(request.body)
    username = data["userName"]
    password = data["password"]
    first_name = data["firstName"]
    last_name = data["lastName"]
    email = data["email"]

    try:
        User.objects.get(username=username)
        return JsonResponse({"userName": username, "error": "Already Registered"})
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email,
        )
        login(request, user)
        return JsonResponse({"userName": username, "status": "Authenticated"})


# Get cars view
def get_cars(request):
    if CarMake.objects.count() == 0:
        initiate()
    car_models = CarModel.objects.select_related("car_make")
    cars = [{"CarModel": cm.name, "CarMake": cm.car_make.name} for cm in car_models]
    return JsonResponse({"CarModels": cars})


# # Update the `get_dealerships` view to render the index page with
# a list of dealerships
def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = f"/fetchDealers/{state}"
    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships})


def get_dealer_reviews(request, dealer_id):
    try:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint) or []

        # Se não houver reviews, cria um exemplo fake
        if not reviews:
            reviews = [
                {
                    "review": "This is a sample review for testing.",
                    "full_name": "Test User",
                    "car_make": "Mazda",
                    "car_model": "MX-5",
                    "purchase_date": "2003-05-12",
                    "sentiment": "neutral",
                }
            ]

        safe_reviews = []
        for review_detail in reviews:
            review = {
                "review": review_detail.get("review", "No review provided"),
                "full_name": review_detail.get("full_name")
                or review_detail.get("name")
                or "Anonymous",
                "car_make": review_detail.get("car_make", "Unknown"),
                "car_model": review_detail.get("car_model", "Unknown"),
                "purchase_date": review_detail.get("purchase_date", "Unknown"),
                "sentiment": review_detail.get("sentiment", "neutral"),
            }
            safe_reviews.append(review)

        return JsonResponse({"status": 200, "reviews": safe_reviews}, safe=False)
    except Exception as e:
        logger.error(f"Erro em get_dealer_reviews: {e}")
        return JsonResponse({"status": 500, "message": str(e)}, status=500)


# Create a `get_dealer_details` view to render the dealer details
def get_dealer_details(request, dealer_id):
    if dealer_id:
        endpoint = "/fetchDealer/" + str(dealer_id)
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})


# Create a `add_review` view to submit a review


def add_review(request):
    if not request.user.is_anonymous:
        data = json.loads(request.body)
        try:
            post_review(data)  # não precisa guardar em 'response' se não usa
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse({"status": 401, "message": "Error in posting review"})
    else:
        return JsonResponse({"status": 403, "message": "Unauthorized"})
