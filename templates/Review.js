import React, { useState, useEffect } from "react";
import axios from "axios";
import ReactStars from "react-rating-stars-component";

const Review = ({ seller }) => {
  const [reviews, setReviews] = useState([]);
  const [rating, setRating] = useState(0);
  const [reviewText, setReviewText] = useState("");

  useEffect(() => {
    axios.get(`/get_reviews/${seller}`).then(response => {
      setReviews(response.data);
    });
  }, [seller]);

  const handleSubmit = async () => {
    await axios.post("/add_review", {
      seller,
      rating,
      review: reviewText,
    });
    setReviewText("");
    window.location.reload();
  };

  return (
    <div>
      <h3>Reviews for {seller}</h3>
      {reviews.map((rev, index) => (
        <div key={index}>
          <ReactStars value={rev.rating} edit={false} />
          <p>{rev.review} - <strong>{rev.buyer}</strong></p>
        </div>
      ))}
      <div>
        <ReactStars count={5} size={30} onChange={setRating} />
        <textarea value={reviewText} onChange={(e) => setReviewText(e.target.value)} />
        <button onClick={handleSubmit}>Submit Review</button>
      </div>
    </div>
  );
};

export default Review;
