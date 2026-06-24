interface User {
    name: string;
    id: number;
}

function greet(user: User): string {
    return `Hello, ${user.name}! Your ID is ${user.id}.`;
}

const newUser: User = {
    name: "Developer",
    id: 1
};

console.log(greet(newUser));
