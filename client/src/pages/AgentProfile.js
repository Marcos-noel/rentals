import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";

function AgentProfile() {
    const [data, setData] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = () => {
        // Retrieve the token from localStorage or wherever it is stored
        const token = localStorage.getItem('token');

        fetch('/agent-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`  // Include the token in the headers
            }
        })
        .then((response) => response.json())
        .then((jsonData) => {
            console.log('Fetched data:', jsonData);
            setData(jsonData);  // Update state with fetched data
        })
        .catch((error) => console.error("Error fetching data:", error));
    };

    if (!data) {
        return <div>Loading...</div>;
    }

    return (
        <>
            <h2>My Profile</h2>
            <div key={data.id}>
                <p>First Name: {data.first_name}</p>
                <p>Last Name: {data.last_name}</p>
                <p>Phone: {data.phone}</p>
                <p>Email: {data.email}</p>
                <p>Description: {data.description}</p>
                <p>Reviews: {data.reviews}</p>
                <p>Zipcode: {data.zipcode}</p>
                <p>No of Properties: {data.no_of_properties}</p>
            </div>

            <Link to="/agent/profile-update">Update Profile</Link>
            <Link to="/agent/add-property">Add Property</Link>
            <Link to="/agent/add-land">Add Land</Link>
            <Link to="/agent/properties">My Properties</Link>
            <Link to="/agent/lands">My Lands</Link>
        </>
    );
}

export default AgentProfile;
