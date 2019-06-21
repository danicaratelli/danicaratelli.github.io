---
layout: archive
title: "Publications"
permalink: /research/
author_profile: true
---

<head>
  <!-- Default head tags -->
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="{{ "/assets/main.css" | relative_url }}">
  <link rel="alternate" type="application/rss+xml" title="{{ site.title | escape }}" href="{{ "/feed.xml" | relative_url }}">

  <!-- Favicon head tag -->
  <link rel="icon" href="../favicon.ico" type="image/x-icon">
</head>


{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

{% for post in site.research reversed %}
  {% include archive-single.html %}
{% endfor %}


Work in Progress
======
* [*Monetary Policy in a Heterogeneous Currency Union*]


Blogs
======
* [*Just Released: Introducing the New York Fed Staff Nowcast*](http://libertystreeteconomics.newyorkfed.org/2016/04/just-released-introducing-the-frbny-nowcast.html), with G. Aarons, M. Cocci, D. Giannone, A. Sbordone, A. Tambalotti
  * check out the [Nowcasting Report](https://libertystreeteconomics.newyorkfed.org/2016/04/just-released-introducing-the-frbny-nowcast.html)
  * in the news [Bloomberg](https://www.bloomberg.com/news/videos/2016-04-13/introducing-the-frbny-nowcast)

* [*Opening the Toolbox: The Nowcasting Code on GitHub*](https://libertystreeteconomics.newyorkfed.org/2018/08/opening-the-toolbox-the-nowcasting-code-on-github.html), with P. Adams, B. Bok, D. Giannone, E. Qian, A. Sbordone, C. Schneier, A. Tambalotti