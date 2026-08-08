import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProjectList from './pages/ProjectList';
import ProjectDetail from './pages/ProjectDetail';
import CustomerList from './pages/CustomerList';
import CustomerDetail from './pages/CustomerDetail';
import ContactDetail from './pages/ContactDetail';
import TaskQueue from './pages/TaskQueue';
import DraftReview from './pages/DraftReview';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<ProjectList />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/customers" element={<CustomerList />} />
        <Route path="/customers/:id" element={<CustomerDetail />} />
        <Route path="/contacts/:id" element={<ContactDetail />} />
        <Route path="/tasks" element={<TaskQueue />} />
        <Route path="/drafts" element={<DraftReview />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  );
}
