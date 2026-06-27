from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from fame.models import ExpertiseAreas, Fame
from fame.serializers import FameSerializer
from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from socialnetwork.models import SocialNetworkUsers
from socialnetwork.serializers import PostsSerializer


@require_http_methods(["GET"])
@login_required
def timeline(request):
    # using the serializer to get the data, then use JSON in the template!
    # avoids having to do the same thing twice

    # initialize community mode to False the first time in the session
    if 'community_mode' not in request.session:
        request.session['community_mode'] = False

    user = _get_social_network_user(request.user)
    community_mode = request.session['community_mode']

    # get extra URL parameters:
    keyword = request.GET.get("search", "")
    published = request.GET.get("published", True)
    error = request.GET.get("error", None)

    # context shared by both branches: community overview and the mode toggle:
    common_context = {
        "error": error,
        "followers": list(api.follows(user).values_list('id', flat=True)),
        "community_mode": community_mode,
        "my_communities": user.communities.all(),
        "joinable_communities": api.joinable_communities(user),
    }

    # if keyword is not empty, use search method of API:
    if keyword and keyword != "":
        context = {
            **common_context,
            "posts": PostsSerializer(
                api.search(keyword, published=published), many=True
            ).data,
            "searchkeyword": keyword,
        }
    else:  # otherwise, use timeline method of API:

        context = {
            **common_context,
            "posts": PostsSerializer(
                api.timeline(
                    user,
                    published=published,
                    community_mode=community_mode,
                ),
                many=True,
            ).data,
            "searchkeyword": "",
        }

    return render(request, "timeline.html", context=context)


@require_http_methods(["POST"])
@login_required
def follow(request):
    user = _get_social_network_user(request.user)
    user_to_follow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.follow(user, user_to_follow)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["POST"])
@login_required
def unfollow(request):
    user = _get_social_network_user(request.user)
    user_to_unfollow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.unfollow(user, user_to_unfollow)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["GET"])
@login_required
def bullshitters(request):
    # call the api to get the bullshitters dictionary
    bs = api.bullshitters()
    context = {
        "bullshitters": bs,
    }
    return render(request, "bullshitters.html", context=context)

@require_http_methods(["POST"])
@login_required
def toggle_community_mode(request):
    request.session["community_mode"] = not request.session.get("community_mode", False)
    request.session.modified = True
    return redirect(reverse("sn:timeline"))

@require_http_methods(["POST"])
@login_required
def join_community(request):
    user = _get_social_network_user(request.user)
    community = ExpertiseAreas.objects.get(id=request.POST.get("community_id"))
    if not api.can_join_community(user, community):
        query = urlencode({"error": "You are not eligible to join this community."})
        return redirect(f"{reverse('sn:timeline')}?{query}")
    api.join_community(user, community)
    return redirect(reverse("sn:timeline"))

@require_http_methods(["POST"])
@login_required
def leave_community(request):
    user = _get_social_network_user(request.user)
    community = ExpertiseAreas.objects.get(id=request.POST.get("community_id"))
    if community not in user.communities.all():
        query = urlencode({"error": "You are not a member of this community."})
        return redirect(f"{reverse('sn:timeline')}?{query}")
    api.leave_community(user, community)
    return redirect(reverse("sn:timeline"))
