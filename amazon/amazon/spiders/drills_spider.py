import re

import scrapy


class QuotesSpider(scrapy.Spider):
    name = "drills"
    page = 0
    page_limit = 5
    start_urls = [
        "https://www.amazon.com/s/page=1&keywords=drill"
    ]

    def parse__(self, response):
        print("NEW PARSE")
        yield scrapy.Request(url="https://www.amazon.com/BLACK-DECKER-LDX120C-Lithium-Driver/dp/B005NNF0YU/", callback=self.get_product_page)

    def parse(self, response):
        print("OLD PARSE")
        print(response)
        tmp = scrapy.Selector(response)
        all_products = tmp.xpath("*//a[contains(@class, 's-access-detail-page')]")
        # next_page = tmp.xpath('*//a[@id="pagnNextLink"]')
        next_page = tmp.css("#pagnNextLink::attr(href)").extract_first()
        for p in all_products:
            product_page_link = response.urljoin(p.xpath("@href").extract_first())
            yield scrapy.Request(url=product_page_link, callback=self.get_product_page)
            print(f"------> {product_page_link}")
        if next_page and self.page <= self.page_limit:
            self.page += 1
            print(f"PAGE: ---------------------------- {self.page}")
            yield response.follow(next_page, callback=self.parse)

    def get_product_page(self, response):
        s = scrapy.Selector(response)
        url = response.url
        asin = re.search(r"(?:\/dp\/([0-9a-zA-Z]*))", url).group(1)

        title = s.xpath('//span[@id="productTitle"]/text()').extract_first().strip()
        all_reviews = s.xpath('//*[@id="dp-summary-see-all-reviews"]')
        for a in all_reviews:
            all_reviews_href = response.urljoin(a.xpath("@href").extract_first())
            request = scrapy.Request(url=all_reviews_href, callback=self.get_all_reviews)
            request.meta["url"] = url
            request.meta["title"] = title
            request.meta["asin"] = asin
            yield request

    def get_all_reviews(self, response):
        s = scrapy.Selector(response)
        url, title, asin = (response.request.meta[x] for x in ["url", "title", "asin"])
        if "page" in response.request.meta:
            page = response.request.meta["page"]
            if page > 5:
                pass
                # print(page)
        reviews = s.xpath('//*[@data-hook="review"]')
        # next_link = s.xpath("//*[@class='a-last']/a")
        n = response.css('li.a-last a::attr(href)').extract_first()
        if n:
            n = response.urljoin(n)
            request = scrapy.Request(url=n, callback=self.get_all_reviews)
            request.meta["url"] = url
            request.meta["title"] = title
            request.meta["asin"] = asin
            if "page" not in response.request.meta:
                response.request.meta["page"] = 1
                request.meta["page"] = 2
            else:
                request.meta["page"] = response.request.meta["page"] + 1
            yield request
            # yield response.follow(n, callback=self.get_all_reviews)
        for review in reviews:
            review_id = review.xpath("@id").extract_first()
            review_body = review.xpath(".//*[@data-hook='review-body']/text()").extract_first()
            rating = re.search("([0-9]\.[0-9])", review.xpath('.//i[@data-hook="review-star-rating"]/span/text()').extract_first()).group(1)
            yield({
                "name": title,
                "url": url,
                "rating": rating,
                "asin": asin,
                "review": review_body,
                "review_id": review_id
            })